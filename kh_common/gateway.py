from aiohttp import ClientTimeout, request as async_request
from kh_common.avro import AvroDeserializer, AvroSerializer
from pydantic import BaseModel, parse_obj_as
from kh_common.caching import KwargsCache
from kh_common.hashing import Hashable
from typing import Any, Dict, Type
from hashlib import md5


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
		self,
		endpoint: str,
		model: Type[BaseModel],
		method: str = 'GET',
		timeout: float = 30
	) -> None :
		self._endpoint: str = endpoint
		self._model: Type[BaseModel] = model
		self._method: str = method.lower()
		self._timeout: float = timeout


	async def __call__(
		self,
		body: dict = None,
		auth: str = None,
		headers: Dict[str, str] = None,
		**kwargs,
	) -> Any :
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

		if headers :
			req['headers'].update(headers)

		if auth :
			req['headers']['authorization'] = 'bearer ' + auth

		async with async_request(
			self._method,
			self._endpoint.format(**kwargs),
			**req,
		) as response :
			data = await response.json()
			return parse_obj_as(self._model, data)


class AvroGateway(Hashable) :

	def __init__(
		self,
		endpoint: str,
		request_model: Type[BaseModel],
		response_model: Type[BaseModel],
		timeout: float = 30
	) -> None :
		self._endpoint: str = endpoint
		self._serializer: AvroSerializer = AvroSerializer(request_model)
		self._response_model: Type[BaseModel] = response_model
		self._timeout: float = timeout
		# these need to be set during the handshake protocol
		self._deserializer: AvroDeserializer
		self._client_protocol: dict
		self._client_hash: bytes


	async def __call__(
		self,
		body: BaseModel,
		auth: str = None,
		headers: Dict[str, str] = None,
		**kwargs,
	) -> Any :
		raise NotImplementedError('this is completely non-functional at the moment')

		req = {
			'timeout': ClientTimeout(self._timeout),
			'raise_for_status': True,
			'headers': {
				'content-type': 'avro/binary',
				'accept': 'avro/binary, application/json',
			},
		}

		req['params'] = body

		if headers :
			req['headers'].update(headers)

		if auth :
			req['headers']['authorization'] = 'bearer ' + auth

		# handshake must be performed here

		async with async_request(
			'POST',  # avro always uses POST - https://avro.apache.org/docs/current/spec.html#HTTP+as+Transport
			self._endpoint.format(**kwargs),
			**req,
		) as response :
			data = await response.body()
			return self._deserializer(data)
