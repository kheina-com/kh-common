import json
from asyncio import sleep
from hashlib import md5
from typing import Any, Callable, Dict, Iterable, Set, Type, Union

from aiohttp import ClientResponse, ClientResponseError, ClientTimeout
from aiohttp import request as async_request
from pydantic import BaseModel, parse_obj_as

from kh_common.avro.handshake import AvroMessage, AvroProtocol, CallRequest, CallResponse, HandshakeMatch, HandshakeRequest, HandshakeResponse
from kh_common.avro.schema import convert_schema, get_name
from kh_common.avro.serialization import AvroDeserializer, AvroSerializer, avro_frame, read_avro_frames
from kh_common.config.repo import name
from kh_common.hashing import Hashable
from kh_common.models import Error, ValidationError

handshake_deserializer: AvroDeserializer = AvroDeserializer(HandshakeResponse)
handshake_serializer: AvroSerializer = AvroSerializer(HandshakeRequest)
call_deserializer: AvroDeserializer = AvroDeserializer(CallResponse)
call_serializer: AvroSerializer = AvroSerializer(CallRequest)


class Gateway(Hashable) :

	def __init__(
		self: 'Gateway',
		endpoint: str,
		protocol: str,
		request_model: Type[BaseModel],
		response_model: Type[BaseModel],
		error_models: Iterable[Type[BaseModel]] = Union[Error, ValidationError],
		attempts: int = 3,
		timeout: float = 30,
		backoff: Callable = lambda attempt : attempt ** 2,
	) -> None :
		self._endpoint: str = endpoint
		self._serializer: AvroSerializer = AvroSerializer(request_model)
		self._response_model: Type[BaseModel] = response_model
		self._timeout: float = timeout
		# these need to be set during the handshake protocol
		self._message_name: str = protocol
		self._deserializer: AvroDeserializer
		self._client_protocol: AvroProtocol = AvroProtocol(
			namespace=name,
			protocol=self._message_name,
			messages={
				self._message_name: AvroMessage(
					request=convert_schema(request_model)['fields'],
					response=get_name(response_model),
					types=list(map(convert_schema, [response_model] + error_models)),
					errors=list(map(get_name, error_models)),
					oneWay=False,
				),
			},
		)
		self._client_hash: bytes = md5(self._client_protocol.json().encode()).digest()
		self._server_hash: bytes = b'deadbeefdeadbeef'
		self._error_deserializer: AvroDeserializer = AvroDeserializer(Union[error_models, str])
		self._attempts: int = attempts
		self._backoff: Callable = backoff


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
			req['headers']['authorization'] = 'bearer ' + str(auth)

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
