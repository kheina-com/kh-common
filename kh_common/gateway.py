from kh_common.avro.handshake import AvroProtocol, AvroMessage, CallRequest, CallResponse, HandshakeRequest, HandshakeResponse, HandshakeMatch
from kh_common.avro.serialization import AvroDeserializer, AvroSerializer, avro_frame, read_avro_frames
from aiohttp import ClientResponseError, ClientResponse, ClientTimeout, request as async_request
from typing import Any, Callable, Dict, Iterable, Set, Type, Union
from kh_common.avro.schema import convert_schema, get_name
from kh_common.models import Error, ValidationError
from pydantic import BaseModel, parse_obj_as
from kh_common.hashing import Hashable
from kh_common.config.repo import name
from asyncio import sleep
from hashlib import md5
import json


handshake_deserializer: AvroDeserializer = AvroDeserializer(HandshakeResponse)
handshake_serializer: AvroSerializer = AvroSerializer(HandshakeRequest)
call_deserializer: AvroDeserializer = AvroDeserializer(CallResponse)
call_serializer: AvroSerializer = AvroSerializer(CallRequest)


class Gateway(Hashable) :

	MethodsWithoutBody = {
		'get',
		'head',
		'delete',
		'options',
		'trace',
		'connect',
	}


	def __init__(
		self: 'Gateway',
		endpoint: str,
		model: Type[BaseModel] = None,
		method: str = 'GET',
		timeout: float = 30,
		attempts: int = 3,
		status_to_retry: Iterable[int] = [429, 502, 503, 504],
		backoff: Callable = lambda attempt : attempt ** 2,
		decoder: Callable = ClientResponse.json,
	) -> None :
		"""
		Defines an endpoint to be called later.
		Url string is defined using python string format. Any keyword arguments passed to the call function will be used to format the url.
		EX: Gateway('https://example.com/post/{post_id}')(post_id=11) will yield a GET request to https://example.com/post/11
		:param endpoint: required, defines the endpoint to be called
		:param model: required, defines the response model to be used as decoder. If the endpoint returns 204, use None.
		:param method: the method used to send requests
		:param timeout: how long to wait, in seconds, for the endpoint to return a response
		:param attempts: how many times to attempt to reach the endpoint, in total
		:param status_to_retry: which http status codes should be retried
		:param backoff: backoff function to run on failure to determine how many seconds to wait before retrying call. Must accept attempt count as param, defaults to attempt ** 2
		:param decoder: async function used to decode the response body. accepts ClientResponse as arg. defaults to ClientResponse.json
		"""
		self._endpoint: str = endpoint
		self._model: Type[BaseModel] = model
		self._method: str = method.lower()
		self._timeout: float = timeout
		self._attempts: int = attempts
		self._status_to_retry: Set[int] = set(status_to_retry)
		self._backoff: Callable = backoff
		self._decoder: Callable = decoder


	async def __call__(
		self: 'Gateway',
		body: dict = None,
		params: dict = None,
		auth: str = None,
		headers: Dict[str, str] = None,
		**kwargs,
	) -> Any :
		"""
		Calls pre-defined endpoint using the provided HTTP method.
		:param body: body will be encoded either as json body or url params if method is contained in self.MethodsWithoutBody
		:param params: same as body, but will always be encoded as url params
		:param headers: headers will be passed to the request
		:param auth: auth will be passed to the authorization as a bearer token (NOTE: auth will override any authorization header passed via headers)
		:param kwargs: any other keyword arguments will be passed to endpoint.format if a string format was provided for the endpoint
		:return: decoded json response using the model provided upon initialization
		:raises: all standard aiohttp errors on failure.
		"""
		req = {
			'timeout': ClientTimeout(self._timeout),
			'raise_for_status': True,
			'headers': {
				'accept': 'application/json',
			},
		}

		if self._method in self.MethodsWithoutBody :
			req['params'] = body

		else :
			req['json'] = body

		if params :
			if 'params' in req :
				req['params'].update(params)

			else :
				req['params'] = params

		if headers :
			req['headers'].update(headers)

		if auth :
			req['headers']['authorization'] = 'Bearer ' + str(auth)

		for attempt in range(1, self._attempts + 1) :
			try :
				async with async_request(
					self._method,
					self._endpoint.format(**kwargs),
					**req,
				) as response :
					if not self._decoder :
						return

					data = await self._decoder(response)

					if not self._model :
						return data

					return parse_obj_as(self._model, data)

			except ClientResponseError as e :
				if e.status not in self._status_to_retry or attempt == self._attempts :
					raise

				await sleep(self._backoff(attempt))


class AvroGateway(Hashable) :

	def __init__(
		self,
		endpoint: str,
		protocol: str,
		request_model: Type[BaseModel],
		response_model: Type[BaseModel],
		error_models: Iterable[Type] = Union[Error, ValidationError],
		timeout: float = 30,
	) -> None :
		self._endpoint: str = endpoint
		self._serializer: AvroSerializer = AvroSerializer(request_model)
		self._response_model: Type[BaseModel] = response_model
		self._timeout: float = timeout
		# these need to be set during the handshake protocol
		self._message_name: str = protocol
		self._deserializer: AvroDeserializer
		self._client_protocol: dict
		self._client_protocol: AvroProtocol = AvroProtocol(
			namespace=name,
			protocol=self._message_name,
			messages={
				self._message_name: AvroMessage(
					request=convert_schema(request_model)['fields'],
					response=get_name(response_model),
					oneWay=False,
					types=list(map(convert_schema, [
						response_model,
						Error,
						ValidationError,
					])),
					errors=list(map(get_name, [
						Error,
						ValidationError,
					])),
				),
			},
		)
		self._client_hash: bytes = md5(self._client_protocol.json().encode).digest()
		self._server_hash: bytes = b'deadbeefdeadbeef'
		self._error_deserializer: AvroDeserializer = AvroDeserializer(Union[error_models, str])


	async def __call__(
		self,
		body: BaseModel,
		auth: str = None,
		headers: Dict[str, str] = None,
		**kwargs,
	) -> Any :

		req = {
			'timeout': ClientTimeout(self._timeout),
			'raise_for_status': True,
			'headers': {
				'content-type': 'avro/binary',
				'accept': 'avro/binary, application/json',
			},
		}

		if headers :
			req['headers'].update(headers)

		if auth :
			req['headers']['authorization'] = 'bearer ' + auth

		# handshake must be performed here
		handshake: HandshakeRequest = HandshakeRequest(
			clientHash=self._client_hash,
			clientProtocol=self._client_protocol.json(),
			serverHash=self._server_hash,
		)


		request: CallRequest = CallRequest(
			message=self._message_name,
			request=self._serializer(body),
		)


		req['data'] = (
			avro_frame(handshake_serializer(handshake)) + 
			avro_frame(call_serializer(request)) + 
			avro_frame()
		)


		async with async_request(
			'POST',  # avro always uses POST - https://avro.apache.org/docs/current/spec.html#HTTP+as+Transport
			self._endpoint.format(**kwargs),
			**req,
		) as response :
			frames = read_avro_frames(await response.body())

			handshake_body: bytes = b''
			handshake: HandshakeResponse
			for frame in frames :
				handshake_body += frame

				try :
					handshake = handshake_deserializer(handshake_body)
					del handshake_body
					break

				except TypeError :
					pass

			assert handshake, 'handshake missing!!'

			if handshake.match == HandshakeMatch.none :
				raise ValueError('protocols are incompatible!')

			elif handshake.match == HandshakeMatch.client :
				server_protocol = json.loads(handshake.serverProtocol)
				server_types = { i['name']: i for i in server_protocol['messages'][self._message_name]['types'] }
				server_response = server_protocol['messages'][self._message_name]['response']

				# optimize: need to handle possibly null responses
				self._deserializer = AvroDeserializer(self._response_model, json.dumps(server_types[server_response] if server_response in server_types else server_response))
				self._server_hash = handshake.serverHash
				# optimize: client protocol and hash need to be updated here too

			call_response: CallResponse
			response_body: bytes = b''
			for frame in frames :
				response_body += frame

				try :
					call_response = call_deserializer(response_body)
					del response_body
					break

				except TypeError :
					pass

			assert call_response, 'response missing!!'

			# optimize: error deserializer needs to be managed as well using the handshake
			if call_response.error :
				raise ValueError(f'error: {self._error_deserializer(call_response.response)}')

			return self._deserializer(call_response.response)
