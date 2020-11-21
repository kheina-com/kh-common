from starlette.middleware.trustedhost import TrustedHostMiddleware
from kh_common.exceptions.base_error import BaseError
from starlette.exceptions import ExceptionMiddleware
from kh_common.exceptions import jsonErrorHandler
from fastapi.responses import UJSONResponse
from kh_common.auth import KhAuthMiddleware
from fastapi import FastAPI, Request


def ServerApp(auth=True, auth_required=True, allowed_hosts={ 'localhost', '127.0.0.1', '*.kheina.com' }) -> FastAPI :
	app = FastAPI()
	app.add_middleware(ExceptionMiddleware, handlers={ Exception: jsonErrorHandler }, debug=False)
	app.add_exception_handler(BaseError, jsonErrorHandler)

	if allowed_hosts :
		app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

	if auth :
		app.add_middleware(KhAuthMiddleware, required=auth_required)

	return app
