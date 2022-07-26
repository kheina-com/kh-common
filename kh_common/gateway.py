from aiohttp import ClientResponseError, ClientResponse, ClientTimeout, request as async_request
from typing import Any, Callable, Dict, Iterable, Set, Type
from pydantic import BaseModel, parse_obj_as
from kh_common.hashing import Hashable
from asyncio import sleep


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
		self._model: Type = model
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
