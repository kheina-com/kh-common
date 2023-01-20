from functools import wraps
from inspect import iscoroutinefunction
from typing import Any, Callable, Dict, Optional, Tuple

from aiohttp import ClientResponseError

from kh_common.config.constants import account_host
from kh_common.gateway import Gateway
from kh_common.models.auth import LoginResponse


BotLogin: Gateway = Gateway(account_host + '/v1/bot_login', LoginResponse, 'POST')


class Client :
	"""
	Defines a fuzz.ly client that can accept a bot token and self-manage authentication
	"""

	def __init__(self: 'Client', token: Optional[str] = None) :
		"""
		:param token: base64 encoded token generated from the fuzz.ly bot creation endpoint
		"""
		self._token: Optional[str] = token
		self._auth: Optional[str] = None


	async def start(self: 'Client') :
		login_response: LoginResponse = await BotLogin({ 'token': self._token })
		self._auth = login_response.token.token


	def authenticated(self: 'Client', func: Gateway) -> Callable :
		if self._token and not self._auth :
			raise ValueError('authorization was not set! was Client.start called during init?')

		if not iscoroutinefunction(func) :
			raise NotImplementedError('provided func is not defined as async. did you pass in a kh_common.gateway.Gateway?')

		@wraps(func)
		async def wrapper(*args: Tuple[Any], **kwargs: Dict[str, Any]) -> Any :
			result: Any

			try :
				result = await func(*args, auth=self._auth, **kwargs)

			except ClientResponseError as e :
				if e.result != 401 or not self._token :
					raise

				# reauthorize
				await self.start()
				# now try re-running
				result = await func(*args, auth=self._auth, **kwargs)

			return result

		return wrapper
