from starlette.types import ASGIApp, Receive, Send, Scope as request_scope
from kh_common.auth import AuthToken, KhUser, retrieveAuthToken, Scope
from kh_common.exceptions.http_error import HttpError, Unauthorized
from kh_common.exceptions import jsonErrorHandler
from starlette.requests import Request


class KhAuthMiddleware:

	def __init__(self, app: ASGIApp, required: bool = True) -> None :
		self.app = app
		self.auth_required = required


	async def __call__(self, scope: request_scope, receive: Receive, send: Send) -> None :
		if scope['type'] not in { 'http', 'websocket' } :
			raise NotImplementedError()

		request: Request = Request(scope, receive, send)

		try :
			token_data: AuthToken = retrieveAuthToken(request)

			scope['user'] = KhUser(
				user_id=token_data.user_id,
				token=token_data,
				scope={ Scope.user } | set(map(Scope.__getitem__, token_data.data.get('scope', []))),
			)

		except HttpError as e :
			if isinstance(e, Unauthorized) and self.auth_required :
				response = jsonErrorHandler(request, e)
				await response(scope, receive, send)
				return

			scope['user'] = KhUser(
				user_id=None,
				token=None,
				scope={ Scope.default },
			)

		await self.app(scope, receive, send)
