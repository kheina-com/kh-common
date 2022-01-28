
from kh_common.avro.handshake import HandshakeRequest, HandshakeResponse, HandshakeMatch, AvroMessage, AvroProtocol, CallRequest, CallResponse
from kh_common.avro import AvroSerializer, AvroDeserializer, avro_frame, read_avro_frames
from kh_common.avro.schema import convert_schema
from fastapi.routing import APIRoute, run_endpoint_function, serialize_response
from avro.compatibility import ReaderWriterCompatibilityChecker, SchemaCompatibilityResult, SchemaCompatibilityType
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from collections import defaultdict, OrderedDict
from starlette.types import ASGIApp, Receive, Send, Scope
from uuid import uuid4
from typing import Iterator, Tuple, Type, Optional, Union, Any, Dict
from fastapi.dependencies.models import Dependant
from fastapi.datastructures import Default, DefaultPlaceholder
import asyncio
from fastapi import params
from fastapi.encoders import DictIntStrAny, SetIntStr
from pydantic.fields import ModelField, Undefined
import json
from fastapi.exceptions import RequestValidationError
from pydantic.error_wrappers import ErrorWrapper
from starlette.exceptions import HTTPException
from fastapi.dependencies.utils import solve_dependencies
import email.message
from hashlib import md5
from avro.schema import parse, Schema
from kh_common.models import Error
from kh_common.config.repo import name
from fastapi.requests import Request
from warnings import warn


AvroChecker = ReaderWriterCompatibilityChecker()


class AvroJsonResponse(JSONResponse) :

	# items are written to the cache in the form of type: writer
	_writer_cache_ = { }

	def __init__(self, serializable_body: dict, model: BaseModel, *args, handshake=None, error=False, **kwargs) :
		super().__init__(serializable_body, *args, **kwargs)
		self._model = model
		self._handshake = handshake
		self._error = error


	async def __call__(self, scope: Scope, receive: Receive, send: Send) :
		request: Request = Request(scope, receive, send)

		if 'avro/binary' in request.headers.get('accept') :

			handshake = self._handshake or request.scope.get('avro_handshake')

			# optimize
			serializer: AvroSerializer = AvroSerializer(type(self._model))

			# optimize
			handshake_serializer: AvroSerializer = AvroSerializer(HandshakeResponse)
			call_serializer: AvroSerializer = AvroSerializer(CallResponse)

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
			self.headers.update({
				'content-length': str(len(self.body)),
				'content-type': 'avro/binary',
			})

		await super().__call__(scope, receive, send)



handshake_deserializer: AvroDeserializer = AvroDeserializer(HandshakeRequest)
call_request_deserializer: AvroDeserializer = AvroDeserializer(CallRequest)


# number of protocols to cache per endpoint
client_protocol_max_size = 10

# format: { endpont_path: { hash: request_deserializer } }
client_protocol_cache = defaultdict(lambda : OrderedDict())


class AvroDecodeError(Exception) :
	pass


def get_client_protocol(handshake: HandshakeRequest, route: APIRoute) -> Tuple[AvroDeserializer, Schema, dict] :
	if handshake.clientHash in client_protocol_cache[route.path] :
		return client_protocol_cache[route.path][handshake.clientHash]

	if handshake.clientProtocol :
		if handshake.clientHash != md5(handshake.clientProtocol.encode()).digest() :
			raise AvroDecodeError('client request protocol and hash did not match. hash must be an md5 hash of the encoded json string protocol.')

		request_schema, response_schema = get_request_schemas(handshake, route)
		# optimize: check if request_schema should be none here, and raise error appropriately
		request_deserializer: Optional[AvroDeserializer] = None

		if route.body_field and request_schema :
			request_deserializer = AvroDeserializer(route.body_field.type_, route.body_schema, request_schema)

		elif route.body_field or request_schema :
			raise AvroDecodeError('client request protocol is incompatible.')

		data = client_protocol_cache[route.path][handshake.clientHash] = request_deserializer, parse(json.dumps(response_schema))

		if len(client_protocol_cache[route.path]) > client_protocol_max_size :
			del client_protocol_cache[route.path][next(reversed(client_protocol_cache[route.path].keys()))]

		return data

	raise AvroDecodeError('client request protocol was not included and client request hash was not cached.')


def get_request_schemas(handshake: HandshakeRequest, route: APIRoute) :
	# optimize
	client_protocol = json.loads(handshake.clientProtocol)
	client_protocol_message = client_protocol.get('messages', { })
	client_protocol_request = client_protocol_message.get(route.path, { })
	client_protocol_response = client_protocol_request.get('response')

	client_protocol_types = { v['name']: v for v in client_protocol_request.get('types', []) }

	if client_protocol_request.get('request') :
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

		if route.body_field :
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


	if client_protocol_response :
		client_protocol_response_schema = (
			client_protocol_types[client_protocol_response]
			if client_protocol_response in client_protocol_types
			else client_protocol_response
		)

	else :
		client_protocol_response_schema = None


	return client_protocol_request_schema, client_protocol_response_schema


def settleAvroHandshake(body: bytes, request: Request, route: APIRoute) -> Any :
	handshake_request: HandshakeRequest = None
	handshake_body: bytes = b''

	frame_gen: Iterator = read_avro_frames(body)
	print(body)

	for frame in frame_gen :
		handshake_body += frame

		try :
			handshake_request = handshake_deserializer(handshake_body)
			del handshake_body
			break

		except TypeError :
			pass

	print(handshake_request)

	if not handshake_request :
		raise AvroDecodeError('There was an error parsing the avro handshake.')

	request_deserializer, client_response_schema = get_client_protocol(handshake_request, route)
	print(request_deserializer, client_response_schema)

	# optimize: can this whole thing be cached with the clienthash?
	response_compatibility: SchemaCompatibilityResult = AvroChecker.get_compatibility(
		# optimize
		reader=client_response_schema,
		# optimize: this should *definitely* be cached
		writer=parse(json.dumps(convert_schema(route.response_model))),
	)

	server_protocol, protocol_hash = get_server_protocol(route)
	print(server_protocol, protocol_hash)

	# optimize
	if handshake_request.serverHash == protocol_hash and response_compatibility.compatibility == SchemaCompatibilityType.compatible :
		request.scope['avro_handshake'] = HandshakeResponse(
			match=HandshakeMatch.both,
		)

	else :
		request.scope['avro_handshake'] = HandshakeResponse(
			match=HandshakeMatch.client,
			serverHash=protocol_hash,
			serverProtocol=server_protocol,
		)

	avro_body: Optional[dict] = None

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

		# optimize: figure out something better to say here
		assert call_request.messageName == route.path, 'request message name must match routh path'

		avro_body = request_deserializer(call_request.request).dict()

	return avro_body


ServerProtocol: Tuple[bytes, str] = None


def get_server_protocol(route: APIRoute) -> Tuple[bytes, str] :
	# optimize: this shouldn't be throwing an error as it's defined above, but it is, so I'm redefining it here
	ServerProtocol: Tuple[bytes, str] = None

	if not ServerProtocol :
		# optimize: this handshake should be generated for the whole app and return all message types
		protocol = AvroProtocol(
			namespace=name,
			protocol=route.path,
			messages={
				route.path: AvroMessage(
					doc='the openapi description should go here. ex: V1Endpoint',
					types=[convert_schema(route.response_model), convert_schema(Error, error=True)],
					# optimize
					request=convert_schema(route.body_field.type_)['fields'] if route.body_field else [],
					# optimize
					response=convert_schema(route.response_model)['name'],
					# find and pass in all error responses below
					# optimize: since this is using ALL possible error responses, this can be globally cached for the whole application
					# like response, this should be a list of strings that point to types in the types list
					errors=list(map(lambda x : convert_schema(x, error=True)['name'], [Error])),
				),
			},
		).json()
		ServerProtocol = protocol, md5(protocol.encode()).digest()

	return ServerProtocol


class AvroRoute(APIRoute) :

	def __init__(self, *args, **kwargs) :
		"""
		in an effort to make this as user-friendly as possible and keep setup to a one-line
		change, we're going to override the `default_response_class` argument, but default
		it in case an endpoint uses a custom response we can't handle
		"""
		kwargs['response_class'] = Default(AvroJsonResponse)
		super().__init__(*args, **kwargs)

		if self.body_field :
			body_schema = convert_schema(self.body_field.type_)
			self.body_schema = parse(json.dumps(body_schema))
			self.schema_name = body_schema['name']
			self.schema_namespace = body_schema['namespace']

		if self.response_model is None and self.status_code not in { 204 } :
			warn('in order for the avro handshake to be performed, a response model must be passed or the status code set to 204')


	def get_route_handler(self) -> ASGIApp :
		# optimize: these don't need to be re-assigned
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
			# optimize
			try :
				body: Any = None
				content_type_value: Optional[str] = request.headers.get('content-type')
				print(content_type_value)

				if content_type_value == 'avro/binary' :
					body_bytes = await request.body()

					if not body_bytes :
						raise AvroDecodeError('no body was included with the avro request. a handshake must be provided with every request')

					avro_body = settleAvroHandshake(body_bytes, request, self)
					body = avro_body

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
								message = email.message.Message()
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
				raise RequestValidationError([ErrorWrapper(e, ('body', e.pos))], body=e.doc)

			except AvroDecodeError :
				# optimize
				server_protocol, protocol_hash = get_server_protocol(self)
				error: str = 'avro handshake failed, client protocol incompatible'
				refid = uuid4()
				# return avro response with full handshake
				return AvroJsonResponse(
					serializable_body={
						'status': 400,
						'error': error,
						'refid': refid.hex,
					},
					model=Error(
						status=400,
						error=error,
						refid=refid.bytes,
					),
					handshake=HandshakeResponse(
						match=HandshakeMatch.none,
						serverProtocol=server_protocol,
						serverHash=protocol_hash,
					),
					error=True,
				)

			except Exception as e :
				raise HTTPException(
					status_code=400, detail='There was an error parsing the body'
				) from e

			solved_result = await solve_dependencies(
				request=request,
				dependant=dependant,
				body=body,
				dependency_overrides_provider=dependency_overrides_provider,
			)
			values, errors, background_tasks, sub_response, _ = solved_result

			if errors :
				raise RequestValidationError(errors, body=body)

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

				response = actual_response_class(response_data, model=raw_response, **response_args)
				response.headers.raw.extend(sub_response.headers.raw)

				if sub_response.status_code :
					response.status_code = sub_response.status_code

				return response

		return app
