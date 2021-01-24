from starlette.middleware.trustedhost import TrustedHostMiddleware
from kh_common.server.middleware.auth import KhAuthMiddleware
from kh_common.server.middleware.cors import KhCorsMiddleware
from kh_common.exceptions.base_error import BaseError
from starlette.exceptions import ExceptionMiddleware
from kh_common.exceptions import jsonErrorHandler
from fastapi import FastAPI, Request


def ServerApp(auth=True, auth_required=True, cors=True, allowed_hosts={ 'localhost', '127.0.0.1', '*.kheina.com', 'kheina.com' }, allowed_protocols={ 'https' }) -> FastAPI :
	app = FastAPI()
	app.add_middleware(ExceptionMiddleware, handlers={ Exception: jsonErrorHandler }, debug=False)
	app.add_exception_handler(BaseError, jsonErrorHandler)

	if allowed_hosts :
		app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

	if auth :
		app.add_middleware(KhAuthMiddleware, required=auth_required)

	if cors :
		app.add_middleware(KhCorsMiddleware, allowed_hosts=allowed_hosts, allowed_protocols=allowed_protocols)

	return app
