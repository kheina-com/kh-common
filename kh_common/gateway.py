from aiohttp import ClientTimeout, request as async_request
from pydantic import BaseModel, parse_obj_as
from kh_common.caching import KwargsCache
from kh_common.hashing import Hashable
from typing import Any, Dict, Type


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
		self._avro: bool = True


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
				'accept': 'avro/binary, application/json',
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