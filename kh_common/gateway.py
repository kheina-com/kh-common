from aiohttp import ClientTimeout, request as async_request
from kh_common.hashing import Hashable
from pydantic import parse_obj_as
from typing import Any, Type


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
		model: Type,
		method: str = 'GET',
		timeout: float = 30
	) -> None :
		self._endpoint: str = endpoint
		self._model: Type = model
		self._method: str = method.lower()
		self._timeout: float = timeout


	async def fetch(
		self,
		body: dict = None,
		auth: str = None,
		**kwargs,
	) -> Any :
		req = {
			'timeout': ClientTimeout(self._timeout),
			'raise_for_status': True,
		}

		if self._method in self.MethodsWithoutBody :
			req['params'] = body

		else :
			req['json'] = body

		if auth :
			req['headers'] = {
				'authorization': 'bearer ' + auth,
			}

		async with async_request(
			self._method,
			self._endpoint.format(**kwargs),
			**req,
		) as response :
			data = await response.json()
			return parse_obj_as(self._model, data)
