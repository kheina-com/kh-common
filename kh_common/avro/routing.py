import asyncio
import json
from asyncio import Lock
from collections import OrderedDict, defaultdict
from email.message import Message as EmailMessage
from enum import Enum
from hashlib import md5
from logging import Logger, getLogger
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Set, Tuple, Type, Union
from warnings import warn

from avro.compatibility import ReaderWriterCompatibilityChecker, SchemaCompatibilityResult, SchemaCompatibilityType
from avro.schema import Schema, parse
from fastapi import params
from fastapi.datastructures import Default, DefaultPlaceholder
from fastapi.dependencies.models import Dependant
from fastapi.dependencies.utils import solve_dependencies
from fastapi.encoders import DictIntStrAny, SetIntStr
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from fastapi.routing import APIRoute, APIRouter, run_endpoint_function, serialize_response
from fastapi.types import DecoratedCallable
from fastapi.utils import generate_unique_id
from pydantic import BaseModel
from pydantic.error_wrappers import ErrorWrapper
from pydantic.fields import ModelField, Undefined
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute
from starlette.types import ASGIApp, Receive, Scope, Send

from kh_common.avro.handshake import MD5, AvroMessage, AvroProtocol, CallRequest, CallResponse, HandshakeMatch, HandshakeRequest, HandshakeResponse
from kh_common.avro.schema import AvroSchema, convert_schema, get_name
from kh_common.avro.serialization import AvroDeserializer, AvroSerializer, avro_frame, read_avro_frames
from kh_common.caching import CalcDict
from kh_common.config.repo import name
from kh_common.models import Error, ValidationError, ValidationErrorDetail
from kh_common.timing import Timer


# number of client protocols to cache per endpoint
# this should be set to something reasonable based on the number of expected consumers per endpoint
# TODO: potentially dynamically set this based on number of clients in a given timeframe?
client_protocol_max_size: int = 10

# format: { route_uniqueid: { md5 hash: (request_deserializer, bool(client compatibility)) } }
client_protocol_cache: Dict[str, Dict[MD5, Tuple[AvroDeserializer, bool]]] = defaultdict(OrderedDict)
cache_locks: Dict[str, Lock] = defaultdict(Lock)

AvroChecker: ReaderWriterCompatibilityChecker = ReaderWriterCompatibilityChecker()
handshake_deserializer: AvroDeserializer = AvroDeserializer(HandshakeRequest)
call_request_deserializer: AvroDeserializer = AvroDeserializer(CallRequest)
handshake_serializer: AvroSerializer = AvroSerializer(HandshakeResponse)
call_serializer: AvroSerializer = AvroSerializer(CallResponse)

logger: Logger = getLogger('avro.routing')
timer: Timer = Timer()


class AvroDecodeError(Exception) :
	pass


class AvroJsonResponse(Response) :

	# items are written to the cache in the form of type: serializer
	# this only occurs with response models, error models are cached elsewhere
	__writer_cache__ = CalcDict(AvroSerializer)

	def __init__(self: 'AvroJsonResponse', serializable_body: dict = None, model: BaseModel = None, *args: Tuple[Any], serializer: AvroSerializer = None, handshake: HandshakeResponse = None, error: bool = False, **kwargs: Dict[str, Any]) :
		super().__init__(None, *args, **kwargs)
		self._serializable_body: Optional[dict] = serializable_body
		self._model: Optional[BaseModel] = model
		self._serializer: Optional[AvroSerializer] = serializer
		self._handshake: Optional[HandshakeResponse] = handshake
		self._error: bool = error


	async def __call__(self: 'AvroJsonResponse', scope: Scope, receive: Receive, send: Send) :
		print(f'AvroJsonResponse.__call__({timer.elapsed()})')
		request: Request = Request(scope, receive, send)

		if 'avro/binary' in request.headers.get('accept') :

			handshake: HandshakeResponse = request.scope['avro_handshake'] if 'avro_handshake' in request.scope else self._handshake
			serializer: AvroSerializer = self._serializer or self.__writer_cache__[type(self._model)]

			if handshake :
				if handshake.match == HandshakeMatch.none or not self._model :
					print('response: handshake only')
					self.body = (
						avro_frame(handshake_serializer(handshake)) +
						avro_frame()
					)

				else :
					print('response: handshake + model')
					self.body = (
						avro_frame(handshake_serializer(handshake)) +
						avro_frame(
							call_serializer(
								CallResponse(
									error=self._error,
									response=serializer(self._model)
								),
							)
						) +
						avro_frame()
					)

			elif self._model :
				print('response: model only')
				self.body = (
					avro_frame(
						call_serializer(
							CallResponse(
								error=self._error,
								response=serializer(self._model)
							),
						)
					) +
					avro_frame()
				)

			else :
				ValueError('at least a handshake or model is required to return an avro response')

			self.status_code = 200
			self.headers['content-type'] = 'avro/binary'

		elif self._serializable_body :
			self.body = json.dumps(self._serializable_body).encode()

		else :
			self.body = self._model.json().encode()

		self.headers['content-length'] = str(len(self.body))

		await super().__call__(scope, receive, send)


async def get_client_protocol(handshake: HandshakeRequest, route: APIRoute) -> Tuple[AvroDeserializer, bool] :
	if handshake.clientHash in client_protocol_cache[route.unique_id] :
		return client_protocol_cache[route.unique_id][handshake.clientHash]

	if handshake.clientProtocol :
		# optimize: do we care about this?
		if handshake.clientHash != md5(handshake.clientProtocol.encode()).digest() :
			raise AvroDecodeError('client request protocol and hash did not match. hash must be an md5 hash of the encoded json string protocol.')

		request_schema, response_schema = get_request_schemas(handshake, route)
		# TODO: check if request_schema should be none here, and raise error appropriately
		request_deserializer: Optional[AvroDeserializer] = None

		if route.body_field and request_schema :
			request_deserializer = AvroDeserializer(route.body_field.type_, route.body_schema, request_schema, parse=False)

		elif route.body_field or request_schema :
			raise AvroDecodeError('client request protocol is incompatible.')

		client_compatible: bool = False
		# print('response_model', response_schema, route.response_model)

		if response_schema :
			if route.response_model :
				# TODO: should this check error responses or only the successful response?
				# TODO: this also needs to check all message types in the CLIENT protocol
				# print('response_schema', response_schema, route.response_schema)
				response_compatibility: SchemaCompatibilityResult = AvroChecker.get_compatibility(
					reader=response_schema,
					# TODO: this should *definitely* be cached
					writer=parse(json.dumps(route.response_schema)),
				)
				client_compatible = response_compatibility.compatibility == SchemaCompatibilityType.compatible

		elif not route.response_model :
			client_compatible = True

		# print('client_compatible', client_compatible)

		data = client_protocol_cache[route.unique_id][handshake.clientHash] = request_deserializer, client_compatible

		if len(client_protocol_cache[route.unique_id]) > client_protocol_max_size :
			# lock required in case two threads try to purge the cache at once
			async with cache_locks[route.unique_id] :
				# fetches all the keys that should be deleted
				for key in list(reversed(client_protocol_cache[route.unique_id].keys()))[len(client_protocol_cache[route.unique_id]) - client_protocol_max_size:] :
					# TODO: potentially track the frequency with which protocols are removed from the cache
					# this should happen infrequently (or never) for greatest efficiency
					del client_protocol_cache[route.unique_id][key]

		return data

	raise AvroDecodeError('client request protocol was not included and client request hash was not cached.')


def get_request_schemas(handshake: HandshakeRequest, route: APIRoute) :
	# optimize
	client_protocol = json.loads(handshake.clientProtocol)
	client_protocol_message = client_protocol.get('messages', { })
	client_protocol_request = client_protocol_message.get(route.unique_id, { })
	client_protocol_response = client_protocol_request.get('response')

	client_protocol_types = { v['name']: v for v in client_protocol_request.get('types', []) }
	client_protocol_request_schema = None

	if client_protocol_request.get('request') :

		if route.body_field :
			client_protocol_request_schema = parse(
				json.dumps({
					'type': 'record',
					'name': route.schema_name,
					'namespace': route.schema_namespace,
					'fields': [
						({ 'type': client_protocol_types[r.pop('type')], **r } if r['type'] in client_protocol_types else r) for r in client_protocol_request['request']
					],
				})
			)

			# optimize
			request_compatibility: SchemaCompatibilityResult = AvroChecker.get_compatibility(
				reader=parse(json.dumps(convert_schema(route.body_field.type_))),
				writer=client_protocol_request_schema,
			)

			if not request_compatibility.compatibility == SchemaCompatibilityType.compatible :
				raise AvroDecodeError('client request protocol is incompatible.')

		else :
			raise AvroDecodeError('client request protocol is incompatible.')

	elif route.body_field :
		raise AvroDecodeError('client request protocol is incompatible.')

	else :
		client_protocol_request_schema = None


	if client_protocol_response != 'null' :
		client_protocol_response_schema = parse(json.dumps(
			client_protocol_types[client_protocol_response]
			if client_protocol_response in client_protocol_types
			else client_protocol_response
		))

	else :
		client_protocol_response_schema = None


	return client_protocol_request_schema, client_protocol_response_schema


async def settleAvroHandshake(body: bytes, request: Request, route: APIRoute) -> Any :
	handshake_request: HandshakeRequest = None
	handshake_body: bytes = b''

	frame_gen: Iterator = read_avro_frames(body)

	for frame in frame_gen :
		handshake_body += frame

		try :
			handshake_request = handshake_deserializer(handshake_body)
			del handshake_body
			break

		except TypeError :
			pass

	# print(handshake_request)

	if not handshake_request :
		raise AvroDecodeError('There was an error parsing the avro handshake.')

	request_deserializer, response_compatibility = await get_client_protocol(handshake_request, route)
	# print(request_deserializer, response_compatibility)

	server_protocol, protocol_hash, _ = get_server_protocol(route, request)
	# print(server_protocol, protocol_hash)

	# optimize
	if handshake_request.serverHash == protocol_hash and response_compatibility :
		request.scope['avro_handshake'] = HandshakeResponse(
			match=HandshakeMatch.both,
		)

	else :
		request.scope['avro_handshake'] = HandshakeResponse(
			match=HandshakeMatch.client,
			serverHash=protocol_hash,
			serverProtocol=server_protocol,
		)

	# print('handshake:', request.scope['avro_handshake'])

	if route.body_field :
		call_request: CallRequest = None
		call_body: bytes = b''

		for frame in frame_gen :
			call_body += frame

			try :
				call_request = call_request_deserializer(call_body)
				del call_body
				break

			except TypeError :
				pass

		if not call_request :
			raise ValueError('There was an error parsing the avro request.')

		# TODO: this may not be right. all methods will need to be coalesced under the POST method, call_request.message should be used to determine which route's handler to use
		assert call_request.message == route.unique_id, f'{call_request.message} not found in valid messages ({route.unique_id})'

		return request_deserializer(call_request.request)


def get_server_protocol(route: APIRoute, request: Request) -> Tuple[str, bytes, AvroSerializer] :
	if route.path in server_protocol_cache :
		return server_protocol_cache[route.path]

	# NOTE: these two errors are used automatically by this library and FastAPI, respectively
	# TODO: this handshake should be generated for all routes that share a url format
	types: List[dict] = [convert_schema(Error, error=True), convert_schema(ValidationError, error=True)]

	# there needs to be a separte refs objects vs enames being a set is due to ordering and
	# serialization/deserialization of a union being order-dependent
	refs = { Error.__name__, ValidationError.__name__ }
	enames = [Error.__name__, ValidationError.__name__]
	errors = Union[Error, ValidationError]

	# print(dir(request.scope['router'].routes[-1]))
	# print(request.scope['router'].routes[-1].__dict__)

	for r in request.scope['router'].routes :
		for status, response in getattr(r, 'responses', { }).items() :
			if status >= 400 and 'model' in response :
				error = convert_schema(response['model'], error=True)
				if error['name'] not in refs :
					# errors = Union[errors, response['model']]
					types.append(error)
					refs.add(error['name'])
					enames.append(error['name'])

	protocol = AvroProtocol(
		namespace=name,
		protocol=route.path,
		messages={
			route.unique_id: AvroMessage(
				doc='the openapi description should go here. ex: V1Endpoint',
				types=types + ([route.response_schema] if route.response_model else []),
				# optimize
				request=convert_schema(route.body_field.type_)['fields'] if route.body_field else [],
				# optimize
				response=route.response_schema['name'] if route.response_model else 'null',
				errors=enames,
			),
		},
	).json()
	server_protocol_cache[route.path] = protocol, md5(protocol.encode()).digest(), AvroSerializer(errors)

	return server_protocol_cache[route.path]


class AvroRoute(APIRoute) :

	def __init__(
		self: 'AvroRoute',
        path: str,
        endpoint: Callable[..., Any],
        *,
        response_model: Any = None,
        status_code: Optional[int] = None,
        tags: Optional[List[Union[str, Enum]]] = None,
        dependencies: Optional[Sequence[params.Depends]] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        response_description: str = 'Successful Response',
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        deprecated: Optional[bool] = None,
        name: Optional[str] = None,
        methods: Optional[Union[Set[str], List[str]]] = None,
        operation_id: Optional[str] = None,
        response_model_include: Optional[Union[SetIntStr, DictIntStrAny]] = None,
        response_model_exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None,
        response_model_by_alias: bool = True,
        response_model_exclude_unset: bool = False,
        response_model_exclude_defaults: bool = False,
        response_model_exclude_none: bool = False,
        include_in_schema: bool = True,
        response_class: Union[Type[Response], DefaultPlaceholder] = Default(AvroJsonResponse),
        dependency_overrides_provider: Optional[Any] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        openapi_extra: Optional[Dict[str, Any]] = None,
        generate_unique_id_function: Union[
            Callable[['APIRoute'], str], DefaultPlaceholder
        ] = Default(generate_unique_id),
	) :
		"""
		in an effort to make this as user-friendly as possible and keep setup to a one-line
		change, we're going to override the `default_response_class` argument, but default
		it in case an endpoint uses a custom response we can't handle
		"""
		# TODO: router will always pass JSONResponse, but we want to override that (for now)
		response_class = Default(AvroJsonResponse)
		status_code = status_code or 200
		super().__init__(
			path,
			endpoint,
			response_model=response_model,
			status_code=status_code,
			tags=tags,
			dependencies=dependencies,
			summary=summary,
			description=description,
			response_description=response_description,
			responses=responses,
			deprecated=deprecated,
			name=name,
			methods=methods,
			operation_id=operation_id,
			response_model_include=response_model_include,
			response_model_exclude=response_model_exclude,
			response_model_by_alias=response_model_by_alias,
			response_model_exclude_unset=response_model_exclude_unset,
			response_model_exclude_defaults=response_model_exclude_defaults,
			response_model_exclude_none=response_model_exclude_none,
			include_in_schema=include_in_schema,
			response_class=response_class,
			dependency_overrides_provider=dependency_overrides_provider,
			callbacks=callbacks,
			openapi_extra=openapi_extra,
			generate_unique_id_function=generate_unique_id_function,
		)

		if self.body_field :
			body_schema = convert_schema(self.body_field.type_)
			self.body_schema = parse(json.dumps(body_schema))
			self.schema_name = body_schema['name']
			self.schema_namespace = body_schema['namespace']

		if self.response_model is None and self.status_code not in { 204 } :
			warn('in order for the avro handshake to be performed, a response model must be passed or the status code set to 204')

		if self.response_model :
			self.response_schema = convert_schema(self.response_model)


	async def handle_avro(self: 'AvroRoute', scope: Scope, receive: Receive, send: Send) -> None :
		print(f'AvroRoute.handle_avro({timer.elapsed()})')
		return await self.app(scope, receive, send)


	def get_route_handler(self: 'AvroRoute') -> ASGIApp :
		# TODO: these don't need to be re-assigned
		dependant: Dependant = self.dependant
		body_field: Optional[ModelField] = self.body_field
		status_code: Optional[int] = self.status_code
		response_class: Union[Type[Response], DefaultPlaceholder] = self.response_class
		response_field: Optional[ModelField] = self.secure_cloned_response_field
		response_model_include: Optional[Union[SetIntStr, DictIntStrAny]] = self.response_model_include
		response_model_exclude: Optional[Union[SetIntStr, DictIntStrAny]] = self.response_model_exclude
		response_model_by_alias: bool = self.response_model_by_alias
		response_model_exclude_unset: bool = self.response_model_exclude_unset
		response_model_exclude_defaults: bool = self.response_model_exclude_defaults
		response_model_exclude_none: bool = self.response_model_exclude_none
		dependency_overrides_provider: Optional[Any] = self.dependency_overrides_provider

		assert dependant.call is not None, 'dependant.call must be a function'

		is_coroutine = asyncio.iscoroutinefunction(dependant.call)
		is_body_form = body_field and isinstance(body_field.field_info, params.Form)

		if isinstance(response_class, DefaultPlaceholder) :
			actual_response_class: Type[Response] = response_class.value

		else :
			actual_response_class = response_class


		async def app(request: Request) -> Response :
			print(f'AvroRoute.app({timer.elapsed()})')
			# optimize
			try :
				body: Any = None
				content_type_value: Optional[str] = request.headers.get('content-type')

				if content_type_value == 'avro/binary' :
					if 'avro_body' in request.scope :
						body = request.scope['avro_body']

					else :
						body_bytes = await request.body()

						if not body_bytes :
							raise AvroDecodeError('no body was included with the avro request. a handshake must be provided with every request')

						body = await settleAvroHandshake(body_bytes, request, self)

				elif body_field :

					if is_body_form :
						body = await request.form()

					else :
						body_bytes = await request.body()

						if body_bytes :
							json_body: Any = Undefined

							if not content_type_value :
								json_body = await request.json()

							else :
								message = EmailMessage()
								message['content-type'] = content_type_value

								if message.get_content_maintype() == 'application' :
									subtype = message.get_content_subtype()

									if subtype == 'json' or subtype.endswith('+json') :
										json_body = await request.json()

							if json_body != Undefined :
								body = json_body

							else :
								body = body_bytes

			except json.JSONDecodeError as e :
				# TODO: this will need to be replaced as well
				# print([ErrorWrapper(e, ('body', e.pos))])
				raise RequestValidationError([ErrorWrapper(e, ('body', e.pos))], body=e.doc)

			except AvroDecodeError :
				server_protocol: str
				protocol_hash: bytes
				serializer: AvroSerializer
				server_protocol, protocol_hash, serializer = request.scope['router']._server_protocol_cache[self.path]
				error: str = 'avro handshake failed, client protocol incompatible'
				print('got AvroDecodeError')

				return AvroJsonResponse(
					model=Error(
						status=400,
						error=error,
					),
					serializer=serializer,
					handshake=HandshakeResponse(
						match=HandshakeMatch.none,
						serverProtocol=server_protocol,
						serverHash=protocol_hash,
					),
					error=True,
				)

			except Exception as e :
				server_protocol: str
				protocol_hash: bytes
				serializer: AvroSerializer
				server_protocol, protocol_hash, serializer = request.scope['router']._server_protocol_cache[self.path]
				error: str = 'There was an error parsing the body: ' + str(e)
				print('got Exception', e)

				return AvroJsonResponse(
					model=Error(
						status=400,
						error=error,
					),
					serializer=serializer,
					handshake=HandshakeResponse(
						match=HandshakeMatch.none,
						serverProtocol=server_protocol,
						serverHash=protocol_hash,
					),
					error=True,
				)

			solved_result = await solve_dependencies(
				request=request,
				dependant=dependant,
				body=body,
				dependency_overrides_provider=dependency_overrides_provider,
			)
			values, errors, background_tasks, sub_response, _ = solved_result
			print(values, errors, background_tasks, sub_response, actual_response_class, self.response_class, f'AvroRoute.solve_dependencies({timer.elapsed()})')

			if errors :
				serializer: AvroSerializer
				_, _, serializer = request.scope['router']._server_protocol_cache[self.path]
				error = ValidationError(detail=[ValidationErrorDetail(**e) for e in errors[0].exc.errors()])
				return AvroJsonResponse(
					model=error,
					serializer=serializer,
					error=True,
				)

			else :
				raw_response = await run_endpoint_function(
					dependant=dependant, values=values, is_coroutine=is_coroutine
				)

				if isinstance(raw_response, Response) :
					if raw_response.background is None :
						raw_response.background = background_tasks
					return raw_response

				response_data = await serialize_response(
					field=response_field,
					response_content=raw_response,
					include=response_model_include,
					exclude=response_model_exclude,
					by_alias=response_model_by_alias,
					exclude_unset=response_model_exclude_unset,
					exclude_defaults=response_model_exclude_defaults,
					exclude_none=response_model_exclude_none,
					is_coroutine=is_coroutine,
				)
				response_args: Dict[str, Any] = { 'background': background_tasks }

				# If status_code was set, use it, otherwise use the default from the
				# response class, in the case of redirect it's 307
				if status_code is not None :
					response_args['status_code'] = status_code

				response = actual_response_class(serializable_body=response_data, model=raw_response, **response_args)
				response.headers.raw.extend(sub_response.headers.raw)

				if sub_response.status_code :
					response.status_code = sub_response.status_code

				return response

		return app


class AvroRouter(APIRouter) :

	def __init__(
		self: 'AvroRouter',
		*,
		prefix: str = '',
		tags: Optional[List[Union[str, Enum]]] = None,
		dependencies: Optional[Sequence[params.Depends]] = None,
		default_response_class: Type[Response] = Default(AvroJsonResponse),
		responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
		callbacks: Optional[List[BaseRoute]] = None,
		routes: Optional[List[BaseRoute]] = None,
		redirect_slashes: bool = True,
		default: Optional[ASGIApp] = None,
		dependency_overrides_provider: Optional[Any] = None,
		route_class: Type[APIRoute] = AvroRoute,
		on_startup: Optional[Sequence[Callable[[], Any]]] = None,
		on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,
		deprecated: Optional[bool] = None,
		include_in_schema: bool = True,
		generate_unique_id_function: Callable[[APIRoute], str] = Default(
			generate_unique_id
		),
	) -> None:
		super().__init__(
			prefix=prefix,
			tags=tags,
			dependencies=dependencies,
			default_response_class=default_response_class,
			responses=responses,
			callbacks=callbacks,
			routes=routes,
			redirect_slashes=redirect_slashes,
			default=default,
			dependency_overrides_provider=dependency_overrides_provider,
			route_class=route_class,
			on_startup=on_startup,
			on_shutdown=on_shutdown,
			deprecated=deprecated,
			include_in_schema=include_in_schema,
			generate_unique_id_function=generate_unique_id_function,
		)

		self._avro_routes: Dict[str, APIRoute] = { route.unique_id: route for route in self.routes }
		# format { route_path: (protocol json, hash, serializer) }
		self._server_protocol_cache: Dict[str, Tuple[str, MD5, AvroSerializer]] = { }
		for route in self.routes :
			self.add_server_protocol(route)

		# number of client protocols to cache per endpoint
		# this should be set to something reasonable based on the number of expected consumers per endpoint
		# optimize: potentially dynamically set this based on number of clients in a given timeframe?
		self._client_protocol_max_size: int = 100

		# format: { md5 hash: (request_deserializer, bool(client compatibility)) }
		self._client_protocol_cache: Dict[MD5, Tuple[AvroDeserializer, bool]] = OrderedDict()
		self._cache_lock: Lock = Lock()


	def add_server_protocol(self: 'AvroRouter', route: APIRoute) -> None :
		if route.path in self._server_protocol_cache :
			p, _, _ = self._server_protocol_cache[route.path]
			protocol: AvroProtocol = AvroProtocol.parse_raw(p)

		else :
			protocol = AvroProtocol(
				namespace=name,
				protocol=route.path,
				messages={ },
			)

		# NOTE: these two errors are used automatically by this library and FastAPI, respectively
		# TODO: this handshake should be generated for all routes that share a url format
		types: List[dict] = [convert_schema(Error, error=True), convert_schema(ValidationError, error=True)]

		# there needs to be a separte refs objects vs enames being a set is due to ordering and
		# serialization/deserialization of a union being order-dependent
		refs = { Error.__name__, ValidationError.__name__ }
		enames = [Error.__name__, ValidationError.__name__]
		errors = Union[Error, ValidationError]

		# print(dir(request.scope['router'].routes[-1]))
		# print(request.scope['router'].routes[-1].__dict__)

		for r in self.routes :
			for status, response in getattr(r, 'responses', { }).items() :
				if status >= 400 and 'model' in response :
					error = convert_schema(response['model'], error=True)
					if error['name'] not in refs :
						# errors = Union[errors, response['model']]
						types.append(error)
						refs.add(error['name'])
						enames.append(error['name'])

		# TODO: we should iterate over the other routes in protocol.messages here to add the new errors and types to other routes

		protocol.messages[route.unique_id] = AvroMessage(
			doc='the openapi description should go here. ex: V1Endpoint',
			types=types + ([route.response_schema] if route.response_model else []),
			# optimize
			request=convert_schema(route.body_field.type_)['fields'] if route.body_field else [],
			# optimize
			response=route.response_schema['name'] if route.response_model else 'null',
			errors=enames,
		)

		protocol_json: str = protocol.json()
		self._server_protocol_cache[route.path] = protocol_json, md5(protocol_json.encode()).digest(), AvroSerializer(errors)


	async def settle_avro_handshake(self: 'AvroRouter', request: Request) -> APIRoute :
		handshake_request: HandshakeRequest = None
		handshake_body: bytes = b''

		body = await request.body()

		if not body :
			raise AvroDecodeError('no body was included with the avro request, a handshake must be provided with every request')

		frame_gen: Iterator = read_avro_frames(body)

		for frame in frame_gen :
			handshake_body += frame

			try :
				handshake_request = handshake_deserializer(handshake_body)
				del handshake_body
				break

			except TypeError :
				pass

		if not handshake_request :
			raise AvroDecodeError('There was an error parsing the avro handshake.')

		request_deserializers, response_compatibility = await self.check_schema_compatibility(handshake_request)
		print(request_deserializers, response_compatibility)

		call_request: CallRequest = None
		call_body: bytes = b''

		for frame in frame_gen :
			call_body += frame

			try :
				call_request = call_request_deserializer(call_body)
				del call_body
				break

			except TypeError :
				pass

		if not call_request :
			raise ValueError('There was an error parsing the avro request.')

		if call_request.message not in self._avro_routes :
			raise AvroDecodeError(f'{call_request.message} not found in valid messages ({", ".join(self._avro_routes.keys())})')

		route: APIRoute = self._avro_routes[call_request.message]
		server_protocol, protocol_hash, _ = self._server_protocol_cache[route.path]
		# print(server_protocol, protocol_hash)

		# optimize
		if handshake_request.serverHash == protocol_hash and response_compatibility :
			request.scope['avro_handshake'] = HandshakeResponse(
				match=HandshakeMatch.both,
			)

		else :
			request.scope['avro_handshake'] = HandshakeResponse(
				match=HandshakeMatch.client,
				serverHash=protocol_hash,
				serverProtocol=server_protocol,
			)

		if call_request.message not in request_deserializers :
			if route.body_field :
				raise AvroDecodeError(f'call request message {call_request.message} was not found in client protocol')

			else :
				request.scope['avro_body'] = None

		elif route.body_field : # optimize: is this check necessary?
			request.scope['avro_body'] = request_deserializers[call_request.message](call_request.request)

		return route


	async def get_client_protocol(self: 'AvroRouter', handshake: HandshakeRequest) -> Tuple[AvroDeserializer, bool] :
		if handshake.clientHash in client_protocol_cache :
			return client_protocol_cache[handshake.clientHash]

		if handshake.clientProtocol :
			request_schema, response_schema = await self.check_schema_compatibility(handshake)
			# TODO: check if request_schema should be none here, and raise error appropriately
			request_deserializer: Optional[AvroDeserializer] = None

			if route.body_field and request_schema :
				request_deserializer = AvroDeserializer(route.body_field.type_, route.body_schema, request_schema, parse=False)

			elif route.body_field or request_schema :
				raise AvroDecodeError('client request protocol is incompatible.')

			client_compatible: bool = False
			# print('response_model', response_schema, route.response_model)

			if response_schema :
				if route.response_model :
					# TODO: should this check error responses or only the successful response?
					# TODO: this also needs to check all message types in the CLIENT protocol
					# print('response_schema', response_schema, route.response_schema)
					response_compatibility: SchemaCompatibilityResult = AvroChecker.get_compatibility(
						reader=response_schema,
						# TODO: this should *definitely* be cached
						writer=parse(json.dumps(route.response_schema)),
					)
					client_compatible = response_compatibility.compatibility == SchemaCompatibilityType.compatible

			elif not route.response_model :
				client_compatible = True

			# print('client_compatible', client_compatible)

			data = client_protocol_cache[route.unique_id][handshake.clientHash] = request_deserializer, client_compatible

			if len(client_protocol_cache[route.unique_id]) > client_protocol_max_size :
				# lock required in case two threads try to purge the cache at once
				async with cache_locks[route.unique_id] :
					# fetches all the keys that should be deleted
					for key in list(reversed(client_protocol_cache[route.unique_id].keys()))[len(client_protocol_cache[route.unique_id]) - client_protocol_max_size:] :
						# TODO: potentially track the frequency with which protocols are removed from the cache
						# this should happen infrequently (or never) for greatest efficiency
						del client_protocol_cache[route.unique_id][key]

			return data

		raise AvroDecodeError('client request protocol was not included and client request hash was not cached.')


	async def check_schema_compatibility(self: 'AvroRouter', handshake: HandshakeRequest) -> Tuple[Dict[str, AvroDeserializer], bool] :
		"""
		returns EMPTY map of route_id -> AvroDeserializer and client compatibility bool
		client compatibility = true: HandshakeMatch.both
		client compatibility = false: HandshakeMatch.client
		raises AvroDecodeError: HandshakeMatch.none
		"""
		if handshake.clientHash in client_protocol_cache :
			return client_protocol_cache[handshake.clientHash]

		if not handshake.clientProtocol :
			raise AvroDecodeError('client request protocol was not included and client request hash was not cached.')

		client_protocol = AvroProtocol.parse_raw(handshake.clientProtocol)
		request_deserializers: Dict[str, AvroDeserializer] = { }
		client_compatible: bool = True

		for route_id, client_message in client_protocol.messages.items() :
			route: APIRoute = self._avro_routes.get(route_id)

			if route is None :
				raise AvroDecodeError(f'route does not exist for client protocol message {route_id}.')

			client_protocol_types = { v['name']: v for v in client_message.types }


			# Check client REQUEST for compatibility
			client_protocol_request_schema = None

			if client_message.request :

				if route.body_field :
					request_schema: AvroSchema = {
						'type': 'record',
						'name': route.schema_name,
						'namespace': route.schema_namespace,
						'fields': [
							({ 'type': client_protocol_types[r.pop('type')], **r } if r['type'] in client_protocol_types else r)
							for r in client_message.request
						],
					}

					client_protocol_request_schema = parse(json.dumps(request_schema))

					# optimize
					request_compatibility: SchemaCompatibilityResult = AvroChecker.get_compatibility(
						reader=parse(json.dumps(convert_schema(route.body_field.type_))),
						writer=client_protocol_request_schema,
					)

					if not request_compatibility.compatibility == SchemaCompatibilityType.compatible :
						raise AvroDecodeError('client request protocol is incompatible.')

					request_deserializers[route.unique_id] = AvroDeserializer(route.body_field.type_, route.body_schema, client_protocol_request_schema, parse=False)

				else :
					raise AvroDecodeError('client protocol provided a request but route does not expect one.')

			elif route.body_field :
				raise AvroDecodeError('client protocol did not provide a request but route expects one.')

			else :
				client_protocol_request_schema = None


			# Check client RESPONSE for compatibility
			if client_message.response != 'null' :
				response_schema = parse(json.dumps(
					client_protocol_types[client_message.response]
					if client_message.response in client_protocol_types
					else client_message.response
				))

			else :
				response_schema = None

			if response_schema :
				if route.response_model :
					# TODO: should this check error responses or only the successful response?
					# TODO: this also needs to check all message types in the CLIENT protocol
					# print('response_schema', response_schema, route.response_schema)
					response_compatibility: SchemaCompatibilityResult = AvroChecker.get_compatibility(
						reader=response_schema,
						# TODO: this should *definitely* be cached
						writer=parse(json.dumps(route.response_schema)),
					)
					client_compatible = client_compatible and response_compatibility.compatibility == SchemaCompatibilityType.compatible

			elif route.response_model :
				client_compatible = False

		data = self._client_protocol_cache[handshake.clientHash] = request_deserializers, client_compatible

		if len(self._client_protocol_cache) > self._client_protocol_max_size :
			# lock required in case two threads try to purge the cache at once
			async with self._cache_lock :
				# fetches all the keys that should be deleted
				for key in list(reversed(self._client_protocol_cache.keys()))[len(self._client_protocol_cache) - self._client_protocol_max_size:] :
					# TODO: potentially track the frequency with which protocols are removed from the cache
					# this should happen infrequently (or never) for greatest efficiency
					del self._client_protocol_cache[key]

		return data


	async def __call__(self: 'AvroRouter', scope: Scope, receive: Receive, send: Send) -> None :
		timer.start()
		print(f'AvroRouter.__call__({timer.elapsed()})')
		if 'avro/binary' in Headers(scope=scope).get('accept') :
			assert scope['type'] in {'http', 'websocket', 'lifespan'}

			if 'router' not in scope :
				scope['router'] = self

			if scope['type'] == 'lifespan' :
				await self.lifespan(scope, receive, send)
				return

			route: AvroRoute = await self.settle_avro_handshake(Request(scope, receive, send))
			print(route, f'({timer.elapsed()})')
			await route.handle_avro(scope, receive, send)
			return

		return await super().__call__(scope, receive, send)


	def add_api_route(
		self: 'AvroRouter',
		path: str,
		endpoint: Callable[..., Any],
		*,
		response_model: Any = None,
		status_code: Optional[int] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		dependencies: Optional[Sequence[params.Depends]] = None,
		summary: Optional[str] = None,
		description: Optional[str] = None,
		response_description: str = 'Successful Response',
		responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
		deprecated: Optional[bool] = None,
		methods: Optional[Union[Set[str], List[str]]] = None,
		operation_id: Optional[str] = None,
		response_model_include: Optional[Union[SetIntStr, DictIntStrAny]] = None,
		response_model_exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None,
		response_model_by_alias: bool = True,
		response_model_exclude_unset: bool = False,
		response_model_exclude_defaults: bool = False,
		response_model_exclude_none: bool = False,
		include_in_schema: bool = True,
		response_class: Union[Type[Response], DefaultPlaceholder] = Default(AvroJsonResponse),
		name: Optional[str] = None,
		route_class_override: Optional[Type[APIRoute]] = None,
		callbacks: Optional[List[BaseRoute]] = None,
		openapi_extra: Optional[Dict[str, Any]] = None,
		generate_unique_id_function: Union[
			Callable[[APIRoute], str], DefaultPlaceholder
		] = Default(generate_unique_id),
	) -> None:
		super().add_api_route(
			path,
			endpoint,
			response_model=response_model,
			status_code=status_code,
			tags=tags,
			dependencies=dependencies,
			summary=summary,
			description=description,
			response_description=response_description,
			responses=responses,
			deprecated=deprecated,
			methods=methods,
			operation_id=operation_id,
			response_model_include=response_model_include,
			response_model_exclude=response_model_exclude,
			response_model_by_alias=response_model_by_alias,
			response_model_exclude_unset=response_model_exclude_unset,
			response_model_exclude_defaults=response_model_exclude_defaults,
			response_model_exclude_none=response_model_exclude_none,
			include_in_schema=include_in_schema,
			response_class=response_class,
			name=name,
			route_class_override=route_class_override,
			callbacks=callbacks,
			openapi_extra=openapi_extra,
			generate_unique_id_function=generate_unique_id_function,
		)
		route = self.routes[-1]
		self._avro_routes[route.unique_id] = route
		self.add_server_protocol(route)

	def get(
		self: 'AvroRouter',
		path: str,
		*,
		response_model: Any = None,
		status_code: Optional[int] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		dependencies: Optional[Sequence[params.Depends]] = None,
		summary: Optional[str] = None,
		description: Optional[str] = None,
		response_description: str = 'Successful Response',
		responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
		deprecated: Optional[bool] = None,
		operation_id: Optional[str] = None,
		response_model_include: Optional[Union[SetIntStr, DictIntStrAny]] = None,
		response_model_exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None,
		response_model_by_alias: bool = True,
		response_model_exclude_unset: bool = False,
		response_model_exclude_defaults: bool = False,
		response_model_exclude_none: bool = False,
		include_in_schema: bool = True,
		response_class: Type[Response] = Default(AvroJsonResponse),
		name: Optional[str] = None,
		callbacks: Optional[List[BaseRoute]] = None,
		openapi_extra: Optional[Dict[str, Any]] = None,
		generate_unique_id_function: Callable[[APIRoute], str] = Default(
			generate_unique_id
		),
	) -> Callable[[DecoratedCallable], DecoratedCallable]:
		return self.api_route(
			path=path,
			response_model=response_model,
			status_code=status_code,
			tags=tags,
			dependencies=dependencies,
			summary=summary,
			description=description,
			response_description=response_description,
			responses=responses,
			deprecated=deprecated,
			methods=['GET'],
			operation_id=operation_id,
			response_model_include=response_model_include,
			response_model_exclude=response_model_exclude,
			response_model_by_alias=response_model_by_alias,
			response_model_exclude_unset=response_model_exclude_unset,
			response_model_exclude_defaults=response_model_exclude_defaults,
			response_model_exclude_none=response_model_exclude_none,
			include_in_schema=include_in_schema,
			response_class=response_class,
			name=name,
			callbacks=callbacks,
			openapi_extra=openapi_extra,
			generate_unique_id_function=generate_unique_id_function,
		)

	def put(
		self: 'AvroRouter',
		path: str,
		*,
		response_model: Any = None,
		status_code: Optional[int] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		dependencies: Optional[Sequence[params.Depends]] = None,
		summary: Optional[str] = None,
		description: Optional[str] = None,
		response_description: str = 'Successful Response',
		responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
		deprecated: Optional[bool] = None,
		operation_id: Optional[str] = None,
		response_model_include: Optional[Union[SetIntStr, DictIntStrAny]] = None,
		response_model_exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None,
		response_model_by_alias: bool = True,
		response_model_exclude_unset: bool = False,
		response_model_exclude_defaults: bool = False,
		response_model_exclude_none: bool = False,
		include_in_schema: bool = True,
		response_class: Type[Response] = Default(AvroJsonResponse),
		name: Optional[str] = None,
		callbacks: Optional[List[BaseRoute]] = None,
		openapi_extra: Optional[Dict[str, Any]] = None,
		generate_unique_id_function: Callable[[APIRoute], str] = Default(
			generate_unique_id
		),
	) -> Callable[[DecoratedCallable], DecoratedCallable]:
		return self.api_route(
			path=path,
			response_model=response_model,
			status_code=status_code,
			tags=tags,
			dependencies=dependencies,
			summary=summary,
			description=description,
			response_description=response_description,
			responses=responses,
			deprecated=deprecated,
			methods=['PUT'],
			operation_id=operation_id,
			response_model_include=response_model_include,
			response_model_exclude=response_model_exclude,
			response_model_by_alias=response_model_by_alias,
			response_model_exclude_unset=response_model_exclude_unset,
			response_model_exclude_defaults=response_model_exclude_defaults,
			response_model_exclude_none=response_model_exclude_none,
			include_in_schema=include_in_schema,
			response_class=response_class,
			name=name,
			callbacks=callbacks,
			openapi_extra=openapi_extra,
			generate_unique_id_function=generate_unique_id_function,
		)

	def post(
		self: 'AvroRouter',
		path: str,
		*,
		response_model: Any = None,
		status_code: Optional[int] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		dependencies: Optional[Sequence[params.Depends]] = None,
		summary: Optional[str] = None,
		description: Optional[str] = None,
		response_description: str = 'Successful Response',
		responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
		deprecated: Optional[bool] = None,
		operation_id: Optional[str] = None,
		response_model_include: Optional[Union[SetIntStr, DictIntStrAny]] = None,
		response_model_exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None,
		response_model_by_alias: bool = True,
		response_model_exclude_unset: bool = False,
		response_model_exclude_defaults: bool = False,
		response_model_exclude_none: bool = False,
		include_in_schema: bool = True,
		response_class: Type[Response] = Default(AvroJsonResponse),
		name: Optional[str] = None,
		callbacks: Optional[List[BaseRoute]] = None,
		openapi_extra: Optional[Dict[str, Any]] = None,
		generate_unique_id_function: Callable[[APIRoute], str] = Default(
			generate_unique_id
		),
	) -> Callable[[DecoratedCallable], DecoratedCallable]:
		return self.api_route(
			path=path,
			response_model=response_model,
			status_code=status_code,
			tags=tags,
			dependencies=dependencies,
			summary=summary,
			description=description,
			response_description=response_description,
			responses=responses,
			deprecated=deprecated,
			methods=['POST'],
			operation_id=operation_id,
			response_model_include=response_model_include,
			response_model_exclude=response_model_exclude,
			response_model_by_alias=response_model_by_alias,
			response_model_exclude_unset=response_model_exclude_unset,
			response_model_exclude_defaults=response_model_exclude_defaults,
			response_model_exclude_none=response_model_exclude_none,
			include_in_schema=include_in_schema,
			response_class=response_class,
			name=name,
			callbacks=callbacks,
			openapi_extra=openapi_extra,
			generate_unique_id_function=generate_unique_id_function,
		)

	def delete(
		self: 'AvroRouter',
		path: str,
		*,
		response_model: Any = None,
		status_code: Optional[int] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		dependencies: Optional[Sequence[params.Depends]] = None,
		summary: Optional[str] = None,
		description: Optional[str] = None,
		response_description: str = 'Successful Response',
		responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
		deprecated: Optional[bool] = None,
		operation_id: Optional[str] = None,
		response_model_include: Optional[Union[SetIntStr, DictIntStrAny]] = None,
		response_model_exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None,
		response_model_by_alias: bool = True,
		response_model_exclude_unset: bool = False,
		response_model_exclude_defaults: bool = False,
		response_model_exclude_none: bool = False,
		include_in_schema: bool = True,
		response_class: Type[Response] = Default(AvroJsonResponse),
		name: Optional[str] = None,
		callbacks: Optional[List[BaseRoute]] = None,
		openapi_extra: Optional[Dict[str, Any]] = None,
		generate_unique_id_function: Callable[[APIRoute], str] = Default(
			generate_unique_id
		),
	) -> Callable[[DecoratedCallable], DecoratedCallable]:
		return self.api_route(
			path=path,
			response_model=response_model,
			status_code=status_code,
			tags=tags,
			dependencies=dependencies,
			summary=summary,
			description=description,
			response_description=response_description,
			responses=responses,
			deprecated=deprecated,
			methods=['DELETE'],
			operation_id=operation_id,
			response_model_include=response_model_include,
			response_model_exclude=response_model_exclude,
			response_model_by_alias=response_model_by_alias,
			response_model_exclude_unset=response_model_exclude_unset,
			response_model_exclude_defaults=response_model_exclude_defaults,
			response_model_exclude_none=response_model_exclude_none,
			include_in_schema=include_in_schema,
			response_class=response_class,
			name=name,
			callbacks=callbacks,
			openapi_extra=openapi_extra,
			generate_unique_id_function=generate_unique_id_function,
		)

	def options(
		self: 'AvroRouter',
		path: str,
		*,
		response_model: Any = None,
		status_code: Optional[int] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		dependencies: Optional[Sequence[params.Depends]] = None,
		summary: Optional[str] = None,
		description: Optional[str] = None,
		response_description: str = 'Successful Response',
		responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
		deprecated: Optional[bool] = None,
		operation_id: Optional[str] = None,
		response_model_include: Optional[Union[SetIntStr, DictIntStrAny]] = None,
		response_model_exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None,
		response_model_by_alias: bool = True,
		response_model_exclude_unset: bool = False,
		response_model_exclude_defaults: bool = False,
		response_model_exclude_none: bool = False,
		include_in_schema: bool = True,
		response_class: Type[Response] = Default(AvroJsonResponse),
		name: Optional[str] = None,
		callbacks: Optional[List[BaseRoute]] = None,
		openapi_extra: Optional[Dict[str, Any]] = None,
		generate_unique_id_function: Callable[[APIRoute], str] = Default(
			generate_unique_id
		),
	) -> Callable[[DecoratedCallable], DecoratedCallable]:
		return self.api_route(
			path=path,
			response_model=response_model,
			status_code=status_code,
			tags=tags,
			dependencies=dependencies,
			summary=summary,
			description=description,
			response_description=response_description,
			responses=responses,
			deprecated=deprecated,
			methods=['OPTIONS'],
			operation_id=operation_id,
			response_model_include=response_model_include,
			response_model_exclude=response_model_exclude,
			response_model_by_alias=response_model_by_alias,
			response_model_exclude_unset=response_model_exclude_unset,
			response_model_exclude_defaults=response_model_exclude_defaults,
			response_model_exclude_none=response_model_exclude_none,
			include_in_schema=include_in_schema,
			response_class=response_class,
			name=name,
			callbacks=callbacks,
			openapi_extra=openapi_extra,
			generate_unique_id_function=generate_unique_id_function,
		)

	def head(
		self: 'AvroRouter',
		path: str,
		*,
		response_model: Any = None,
		status_code: Optional[int] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		dependencies: Optional[Sequence[params.Depends]] = None,
		summary: Optional[str] = None,
		description: Optional[str] = None,
		response_description: str = 'Successful Response',
		responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
		deprecated: Optional[bool] = None,
		operation_id: Optional[str] = None,
		response_model_include: Optional[Union[SetIntStr, DictIntStrAny]] = None,
		response_model_exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None,
		response_model_by_alias: bool = True,
		response_model_exclude_unset: bool = False,
		response_model_exclude_defaults: bool = False,
		response_model_exclude_none: bool = False,
		include_in_schema: bool = True,
		response_class: Type[Response] = Default(AvroJsonResponse),
		name: Optional[str] = None,
		callbacks: Optional[List[BaseRoute]] = None,
		openapi_extra: Optional[Dict[str, Any]] = None,
		generate_unique_id_function: Callable[[APIRoute], str] = Default(
			generate_unique_id
		),
	) -> Callable[[DecoratedCallable], DecoratedCallable]:
		return self.api_route(
			path=path,
			response_model=response_model,
			status_code=status_code,
			tags=tags,
			dependencies=dependencies,
			summary=summary,
			description=description,
			response_description=response_description,
			responses=responses,
			deprecated=deprecated,
			methods=['HEAD'],
			operation_id=operation_id,
			response_model_include=response_model_include,
			response_model_exclude=response_model_exclude,
			response_model_by_alias=response_model_by_alias,
			response_model_exclude_unset=response_model_exclude_unset,
			response_model_exclude_defaults=response_model_exclude_defaults,
			response_model_exclude_none=response_model_exclude_none,
			include_in_schema=include_in_schema,
			response_class=response_class,
			name=name,
			callbacks=callbacks,
			openapi_extra=openapi_extra,
			generate_unique_id_function=generate_unique_id_function,
		)

	def patch(
		self: 'AvroRouter',
		path: str,
		*,
		response_model: Any = None,
		status_code: Optional[int] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		dependencies: Optional[Sequence[params.Depends]] = None,
		summary: Optional[str] = None,
		description: Optional[str] = None,
		response_description: str = 'Successful Response',
		responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
		deprecated: Optional[bool] = None,
		operation_id: Optional[str] = None,
		response_model_include: Optional[Union[SetIntStr, DictIntStrAny]] = None,
		response_model_exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None,
		response_model_by_alias: bool = True,
		response_model_exclude_unset: bool = False,
		response_model_exclude_defaults: bool = False,
		response_model_exclude_none: bool = False,
		include_in_schema: bool = True,
		response_class: Type[Response] = Default(AvroJsonResponse),
		name: Optional[str] = None,
		callbacks: Optional[List[BaseRoute]] = None,
		openapi_extra: Optional[Dict[str, Any]] = None,
		generate_unique_id_function: Callable[[APIRoute], str] = Default(
			generate_unique_id
		),
	) -> Callable[[DecoratedCallable], DecoratedCallable]:
		return self.api_route(
			path=path,
			response_model=response_model,
			status_code=status_code,
			tags=tags,
			dependencies=dependencies,
			summary=summary,
			description=description,
			response_description=response_description,
			responses=responses,
			deprecated=deprecated,
			methods=['PATCH'],
			operation_id=operation_id,
			response_model_include=response_model_include,
			response_model_exclude=response_model_exclude,
			response_model_by_alias=response_model_by_alias,
			response_model_exclude_unset=response_model_exclude_unset,
			response_model_exclude_defaults=response_model_exclude_defaults,
			response_model_exclude_none=response_model_exclude_none,
			include_in_schema=include_in_schema,
			response_class=response_class,
			name=name,
			callbacks=callbacks,
			openapi_extra=openapi_extra,
			generate_unique_id_function=generate_unique_id_function,
		)

	def trace(
		self: 'AvroRouter',
		path: str,
		*,
		response_model: Any = None,
		status_code: Optional[int] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		dependencies: Optional[Sequence[params.Depends]] = None,
		summary: Optional[str] = None,
		description: Optional[str] = None,
		response_description: str = 'Successful Response',
		responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
		deprecated: Optional[bool] = None,
		operation_id: Optional[str] = None,
		response_model_include: Optional[Union[SetIntStr, DictIntStrAny]] = None,
		response_model_exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None,
		response_model_by_alias: bool = True,
		response_model_exclude_unset: bool = False,
		response_model_exclude_defaults: bool = False,
		response_model_exclude_none: bool = False,
		include_in_schema: bool = True,
		response_class: Type[Response] = Default(AvroJsonResponse),
		name: Optional[str] = None,
		callbacks: Optional[List[BaseRoute]] = None,
		openapi_extra: Optional[Dict[str, Any]] = None,
		generate_unique_id_function: Callable[[APIRoute], str] = Default(
			generate_unique_id
		),
	) -> Callable[[DecoratedCallable], DecoratedCallable]:

		return self.api_route(
			path=path,
			response_model=response_model,
			status_code=status_code,
			tags=tags,
			dependencies=dependencies,
			summary=summary,
			description=description,
			response_description=response_description,
			responses=responses,
			deprecated=deprecated,
			methods=['TRACE'],
			operation_id=operation_id,
			response_model_include=response_model_include,
			response_model_exclude=response_model_exclude,
			response_model_by_alias=response_model_by_alias,
			response_model_exclude_unset=response_model_exclude_unset,
			response_model_exclude_defaults=response_model_exclude_defaults,
			response_model_exclude_none=response_model_exclude_none,
			include_in_schema=include_in_schema,
			response_class=response_class,
			name=name,
			callbacks=callbacks,
			openapi_extra=openapi_extra,
			generate_unique_id_function=generate_unique_id_function,
		)