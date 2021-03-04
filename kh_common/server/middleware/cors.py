from starlette.types import ASGIApp, Receive, Send, Message, Scope as request_scope
from kh_common.auth import AuthToken, KhUser, retrieveAuthToken, Scope
from kh_common.exceptions.http_error import HttpError, BadRequest
from starlette.datastructures import Headers, MutableHeaders
from kh_common.exceptions import jsonErrorHandler
from starlette.requests import Request
from fastapi.responses import Response
from urllib.parse import urlparse
from functools import partial
from typing import Iterable

class KhCorsMiddleware:

	def __init__(
		self,
		app: ASGIApp,
		allowed_origins: Iterable[str],
		allowed_protocols: Iterable[str] = ['https'],
		allowed_headers: Iterable[str] = [],
		allowed_methods: Iterable[str] = [],
		allow_credentials: bool = True,
		exposed_headers: Iterable[str] = [],
		max_age: int=86400,
	) -> None :
		self.app = app
		self.allowed_origins = set(allowed_origins)
		self.allowed_protocols = set(allowed_protocols)
		self.allowed_headers = ', '.join(allowed_headers + ['access-control-request-method', 'origin'])
		self.allowed_methods = ', '.join(map(str.upper, allowed_methods))
		self.allow_credentials = str(allow_credentials).lower()
		self.exposed_headers = ', '.join(exposed_headers)
		self.max_age = str(max_age)


	async def __call__(self, scope: request_scope, receive: Receive, send: Send) -> None :
		if scope['type'] != 'http' :
			await self.app(scope, receive, send)
			return

		request: Request = Request(scope, receive, send)

		if 'origin' in request.headers :
			origin = urlparse(request.headers['origin'])

			if origin.scheme not in self.allowed_protocols or origin.netloc.split(':')[0] not in self.allowed_origins :
				response = jsonErrorHandler(request, BadRequest('Origin not allowed.'))
				await response(scope, receive, send)
				return

			if request.method == 'OPTIONS' and 'access-control-request-method' in request.headers :
				await Response(
					None,
					status_code=204,
					headers={
						'access-control-allow-origin': origin.geturl(),
						'access-control-allow-methods': self.allowed_methods,
						'access-control-allow-headers': self.allowed_headers,
						'access-control-allow-credentials': self.allow_credentials,
						'access-control-max-age': self.max_age,
						'access-control-expose-headers': self.exposed_headers,
					},
				)(scope, receive, send)
				return

			send = partial(self.send, send=send, headers=request.headers)

		await self.app(scope, receive, send)


	async def send(self, message: Message, send: Send, headers: Headers) -> None :
		if message['type'] != 'http.response.start':
			await send(message)
			return

		origin = headers['origin']
		message.setdefault('headers', [])
		headers = MutableHeaders(scope=message)

		headers.update({
			'access-control-allow-origin': origin,
			'access-control-allow-methods': self.allowed_methods,
			'access-control-allow-headers': self.allowed_headers,
			'access-control-allow-credentials': self.allow_credentials,
			'access-control-max-age': self.max_age,
			'access-control-expose-headers': self.exposed_headers,
		})

		await send(message)
