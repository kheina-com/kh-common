from collections import defaultdict, OrderedDict
from starlette.types import ASGIApp, Receive, Send, Scope as request_scope
from starlette.middleware.trustedhost import TrustedHostMiddleware
from kh_common.server.middleware import CustomHeaderMiddleware
from kh_common.server.middleware.auth import KhAuthMiddleware
from kh_common.server.middleware.cors import KhCorsMiddleware
from kh_common.exceptions.base_error import BaseError
from starlette.exceptions import ExceptionMiddleware
from fastapi.responses import JSONResponse, Response
from kh_common.config.constants import environment
from kh_common.exceptions import jsonErrorHandler
# from kh_common.caching import SimpleCache
from fastapi import FastAPI, Request
from kh_common.models import Error
from pydantic import BaseModel
from uuid import uuid4
from typing import Callable, Iterable, Iterator, Tuple, Type


from fastapi.routing import APIRoute, run_endpoint_function, serialize_response
from avro.compatibility import ReaderWriterCompatibilityChecker, SchemaCompatibilityResult, SchemaCompatibilityType


AvroChecker = ReaderWriterCompatibilityChecker()
NoContentResponse = Response(None, status_code=204)


def ServerApp(
	auth: bool = True,
	auth_required: bool = True,
	cors: bool = True,
	max_age: int = 86400,
	custom_headers: bool = True,
	allowed_hosts: Iterable[str] = [
		'localhost',
		'127.0.0.1',
		'*.kheina.com',
		'kheina.com',
	],
	allowed_origins: Iterable[str] = [
		'localhost',
		'127.0.0.1',
		'dev.kheina.com',
		'kheina.com',
	],
	allowed_methods: Iterable[str] = [
		'GET',
		'POST',
	],
	allowed_headers: Iterable[str] = [
		'accept',
		'accept-language',
		'authorization',
		'cache-control',
		'content-encoding',
		'content-language',
		'content-length',
		'content-security-policy',
		'content-type',
		'cookie',
		'host',
		'location',
		'referer',
		'referrer-policy',
		'set-cookie',
		'user-agent',
		'www-authenticate',
		'x-frame-options',
		'x-xss-protection',
	],
	exposed_headers: Iterable[str] = [
		'authorization',
		'cache-control',
		'content-type',
		'cookie',
		'set-cookie',
		'www-authenticate',
	],
) -> FastAPI :
	app = FastAPI()
	app.router.route_class = AvroRoute
	app.add_middleware(ExceptionMiddleware, handlers={ Exception: jsonErrorHandler }, debug=False)
	app.add_exception_handler(BaseError, jsonErrorHandler)

	allowed_protocols = ['http', 'https'] if environment.is_local() else ['https']

	if custom_headers :
		app.middleware('http')(CustomHeaderMiddleware)

	if cors :
		app.add_middleware(
			KhCorsMiddleware,
			allowed_origins = set(allowed_origins),
			allowed_protocols = set(allowed_protocols),
			allowed_headers = allowed_headers,
			allowed_methods = allowed_methods,
			exposed_headers = exposed_headers,
			max_age = max_age,
		)

	if allowed_hosts :
		app.add_middleware(TrustedHostMiddleware, allowed_hosts=set(allowed_hosts))

	if auth :
		app.add_middleware(KhAuthMiddleware, required=auth_required)

	return app


from kh_common.avro.handshake import HandshakeRequest, HandshakeResponse, HandshakeMatch, AvroMessage, AvroProtocol, CallRequest, CallResponse, HandshakeRequestSchema, HandshakeResponseSchema
from kh_common.avro import AvroSerializer, AvroDeserializer, avro_frame, read_avro_frames
from kh_common.avro.schema import convert_schema


class AvroJsonResponse(JSONResponse) :

	# items are written to the cache in the form of type: writer
	_writer_cache_ = { }

	def __init__(self, serializable_body: dict, model: BaseModel, handshake: HandshakeResponse, *args, **kwargs) :
		super().__init__(serializable_body, *args, **kwargs)
		self._handshake = handshake
		self._model = model


	async def __call__(self, scope: request_scope, receive: Receive, send: Send) :
		request: Request = Request(scope, receive, send)

		if 'avro/binary' in request.headers.get('accept') :

			# optimize
			serializer: AvroSerializer = AvroSerializer(type(self._model))

			# optimize
			handshake_serializer: AvroSerializer = AvroSerializer(HandshakeResponseSchema)
			call_serializer: AvroSerializer = AvroSerializer(CallResponse)

			if self._handshake :
				if self._model :
					self.body = call_serializer(
						CallResponse(
							error=False,
							messageResponse=(
								avro_frame(handshake_serializer(self._handshake)) +
								avro_frame(serializer(self._model)) +
								avro_frame()
							),
						)
					)

				else :
					self.body = call_serializer(
						CallResponse(
							error=False,
							messageResponse=(
								avro_frame(handshake_serializer(self._handshake)) +
								avro_frame()
							),
						)
					)

			else :
				self.body = call_serializer(
					CallResponse(
						error=False,
						messageResponse=(
							avro_frame(serializer(self._model)) +
							avro_frame()
						),
					)
				)

			self.status = 200
			self.headers.update({
				'content-length': str(len(self.body)),
				'content-type': 'avro/binary',
			})

		await super().__call__(scope, receive, send)


from typing import Optional, Union, Type, Any, Dict
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
from functools import lru_cache
from hashlib import md5
from avro.schema import parse, Schema


handshake_deserializer: AvroDeserializer = AvroDeserializer(HandshakeRequest, HandshakeRequestSchema)
call_request_deserializer: AvroDeserializer = AvroDeserializer(CallRequest)


# number of protocols to cache per endpoint
client_protocol_max_size = 10

# format: { endpont_path: { hash: request_deserializer } }
client_protocol_cache = defaultdict(lambda : OrderedDict())


class AvroDecodeError(Exception) :
	pass


def get_client_protocol(handshake: HandshakeRequest, route: APIRoute) -> Tuple[AvroDeserializer, Schema, dict] :
	print(handshake.clientHash, handshake.clientProtocol, client_protocol_cache)
	if handshake.clientHash in client_protocol_cache[route.path] :
		return client_protocol_cache[route.path][handshake.clientHash]

	if handshake.clientProtocol :
		if handshake.clientHash != md5(handshake.clientProtocol.encode()).digest() :
			raise AvroDecodeError('client request protocol and hash did not match. hash must be an md5 hash of the encoded json string protocol.')

		request_schema, response_schema = get_request_schemas(handshake, route)
		# optimize: check if request_schema should be none here, and raise error appropriately
		request_deserializer = AvroDeserializer(route.body_field.type_, route.body_schema, request_schema)
		data = client_protocol_cache[route.path][handshake.clientHash] = request_deserializer, response_schema
		# optimize: remove the least used item from cache if len(client_protocol_cache[route.path]) > client_protocol_max_size
		return data

	raise AvroDecodeError('client request protocol was not included and client request hash was not cached.')


def get_request_schemas(handshake: HandshakeRequest, route: APIRoute) :
	# optimize
	client_protocol = json.loads(handshake.clientProtocol)
	client_protocol_message = client_protocol.get('messages', { })
	client_protocol_request = client_protocol_message.get(route.path, { })
	client_protocol_response = client_protocol_request.get('response')

	client_protocol_types = { v['name']: v for v in client_protocol_request.get('types', []) }

	if client_protocol_request :
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

	else :
		raise AvroDecodeError('client request protocol is incompatible.')

	if client_protocol_response :
		client_protocol_response_schema = (
			client_protocol_types[client_protocol_request['response']]
			if client_protocol_request['response'] in client_protocol_types
			else client_protocol_request['response']
		)

	else :
		client_protocol_response_schema = None

	return client_protocol_request_schema, client_protocol_response_schema


def settleAvroHandshake(body: bytes, route: APIRoute) :
	call_request: CallRequest = call_request_deserializer(body)
	assert call_request.messageName == route.path

	body = call_request.parameters
	handshake_request: HandshakeRequest = None
	handshake_body: bytes = b''

	frame_gen: Iterator = read_avro_frames(body)

	for frame in frame_gen :
		handshake_body += frame

		try :
			handshake_request = handshake_deserializer(handshake_body)
			break

		except TypeError :
			pass

	if not handshake_request :
		raise ValueError('There was an error parsing the avro handshake.')

	request_deserializer, client_response_schema = get_client_protocol(handshake_request, route)

	request: route.body_field.type_ = None
	request_body: bytes = b''

	for frame in frame_gen :
		request_body += frame

		try :
			request = request_deserializer(request_body)
			break

		except TypeError :
			pass

	if not request :
		raise ValueError('There was an error parsing the avro request.')

	return request, client_response_schema


from kh_common.config.repo import name


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
					types=[convert_schema(route.secure_cloned_response_field.type_)],
					# optimize
					request=convert_schema(route.body_field.type_)['fields'],
					# optimize
					response=convert_schema(route.secure_cloned_response_field.type_)['name'],
					# find and pass in all error responses below
					# optimize, since this is using ALL possible error responses, this can be globally cached for the whole application
					# like response, this should be a list of strings that point to types in the types list
					errors=list(map(lambda x : convert_schema(x, error=True), [Error])),
				),
			},
		).json()
		ServerProtocol = md5(protocol.encode()).digest(), protocol

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
		body_schema = convert_schema(self.body_field.type_)
		self.body_schema = parse(json.dumps(body_schema))
		self.schema_name = body_schema['name']
		self.schema_namespace = body_schema['namespace']


	def get_route_handler(self) -> Callable :
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
			client_response_schema = None
			try:
				body: Any = None

				if body_field :

					if is_body_form :
						body = await request.form()

					else :
						body_bytes = await request.body()

						if body_bytes :
							json_body: Any = Undefined
							content_type_value = request.headers.get('content-type')

							if not content_type_value :
								json_body = await request.json()

							else :
								message = email.message.Message()
								message['content-type'] = content_type_value

								if message.get_content_maintype() == 'application' :
									subtype = message.get_content_subtype()

									if subtype == 'json' or subtype.endswith('+json') :
										json_body = await request.json()
								
								elif message.get_content_maintype() == 'avro' :
									subtype = message.get_content_subtype()

									if subtype == 'binary' :
										avro_body, client_response_schema = settleAvroHandshake(body_bytes, self)
										json_body = avro_body.dict()

							if json_body != Undefined:
								body = json_body

							else:
								body = body_bytes

			except json.JSONDecodeError as e :
				raise RequestValidationError([ErrorWrapper(e, ('body', e.pos))], body=e.doc)
			
			except AvroDecodeError :
				# optimize
				protocol_match: HandshakeMatch = HandshakeMatch.none
				server_protocol, protocol_hash = get_server_protocol(self)
				# return avro response with full handshake
				return AvroJsonResponse(
					{
						'status': 400,
						'error': 'whoops, client incompatible!',
						'refid': uuid4().hex,
					},
					Error,
					HandshakeResponse(
						match=HandshakeMatch.none,
						serverProtocol=server_protocol,
						serverHash=protocol_hash
					),
				)

			except Exception as e :
				print(e)
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

			if errors:
				raise RequestValidationError(errors, body=body)

			else:
				# can I create the handshake here and attach it to the request somehow?
				# inject into the scope maybe?

				raw_response = await run_endpoint_function(
					dependant=dependant, values=values, is_coroutine=is_coroutine
				)

				if isinstance(raw_response, Response):
					if raw_response.background is None:
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
				if status_code is not None:
					response_args['status_code'] = status_code

				# optimize
				response_compatibility: SchemaCompatibilityResult = AvroChecker.get_compatibility(
					# optimize
					reader=parse(json.dumps(client_response_schema)),
					# optimize
					writer=parse(json.dumps(convert_schema(type(raw_response)))),
				)

				protocol_match: HandshakeMatch = HandshakeMatch.client

				if response_compatibility.compatibility == SchemaCompatibilityType.compatible :
					protocol_match = HandshakeMatch.both

				avro_handshake: HandshakeResponse = None
				server_protocol, protocol_hash = get_server_protocol(self)

				# optimize
				if protocol_match == HandshakeMatch.both :
					avro_handshake = HandshakeResponse(
						match=protocol_match,
					)

				else :
					avro_handshake = HandshakeResponse(
						match=protocol_match,
						serverHash=protocol_hash,
						serverProtocol=server_protocol,
					)

				response = actual_response_class(response_data, model=raw_response, handshake=avro_handshake, **response_args)
				response.headers.raw.extend(sub_response.headers.raw)

				if sub_response.status_code:
					response.status_code = sub_response.status_code

				return response

		return app
