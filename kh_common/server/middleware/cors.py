from starlette.types import ASGIApp, Receive, Send, Scope as request_scope
from kh_common.auth import AuthToken, KhUser, retrieveAuthToken, Scope
from kh_common.exceptions.http_error import HttpError, BadRequest
from kh_common.exceptions import jsonErrorHandler
from starlette.requests import HTTPConnection
from urllib.parse import urlparse
from typing import Iterable


class KhCorsMiddleware:

	def __init__(self, app: ASGIApp, allowed_hosts: Iterable[str], allowed_protocols: Iterable[str] = ['https']) -> None :
		self.app = app
		self.allowed_hosts = set(allowed_hosts)
		self.allowed_protocols = set(allowed_protocols)


	async def __call__(self, scope: request_scope, receive: Receive, send: Send) -> None :
		if scope['type'] not in { 'http', 'websocket' } :
			raise NotImplementedError()

		request: HTTPConnection = HTTPConnection(scope)

		if 'origin' in request.headers :
			origin = urlparse(request.headers['origin'])
			if origin.scheme not in self.allowed_protocols or origin.netloc.split(':')[0] not in self.allowed_hosts :
				response = jsonErrorHandler(request, BadRequest('Origin not allowed.'))
				await response(scope, receive, send)
				return

		await self.app(scope, receive, send)
