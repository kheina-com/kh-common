from kh_common.auth import AuthToken, InvalidToken, KhUser, retrieveAuthToken, Scope
from kh_common.exceptions.http_error import BadRequest, HttpError, Unauthorized
from starlette.types import ASGIApp, Receive, Send, Scope as request_scope
from kh_common.exceptions import jsonErrorHandler
from starlette.requests import Request


class AvroMiddleware:

	def __init__(self, app: ASGIApp) -> None :
		self.app = app


	async def __call__(self, scope: request_scope, receive: Receive, send: Send) -> None :
		if scope['type'] != 'http' :
			raise NotImplementedError()

		request: Request = Request(scope, receive, send)
		print(self.app)

		await self.app(scope, receive, send)
