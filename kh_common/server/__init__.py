from starlette.middleware.trustedhost import TrustedHostMiddleware
from kh_common.server.middleware.auth import KhAuthMiddleware
from kh_common.exceptions.base_error import BaseError
from fastapi.responses import PlainTextResponse, UJSONResponse
from starlette.exceptions import ExceptionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from kh_common.exceptions import jsonErrorHandler
from fastapi import FastAPI, Request


def ServerApp(
	auth=True,
	auth_required=True,
	cors=True,
	allowed_hosts=['localhost', '127.0.0.1', '*.kheina.com', 'kheina.com'],
	allowed_origins=[r'https?://localhost(?::\d+)?', r'https://(?:\w+\.)?kheina\.com'],
	allow_credentials=True,
	allow_methods=['*'],
	allow_headers=['*'],
	expose_headers=[],
	max_age=600,
) -> FastAPI :
	app = FastAPI()
	app.add_middleware(ExceptionMiddleware, handlers={ Exception: jsonErrorHandler }, debug=False)
	app.add_exception_handler(BaseError, jsonErrorHandler)

	if allowed_hosts :
		app.add_middleware(TrustedHostMiddleware, allowed_hosts=set(allowed_hosts))

	if auth :
		app.add_middleware(KhAuthMiddleware, required=auth_required)

	if cors :
		app.add_middleware(
			CORSMiddleware,
			allow_origin_regex='|'.join(allowed_origins),
			allow_credentials=allow_credentials,
			allow_methods=allow_methods,
			allow_headers=allow_headers,
			expose_headers=expose_headers,
		)

	return app
