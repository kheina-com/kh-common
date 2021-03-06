from starlette.middleware.trustedhost import TrustedHostMiddleware
from kh_common.server.middleware.auth import KhAuthMiddleware
from kh_common.server.middleware.cors import KhCorsMiddleware
from kh_common.exceptions.base_error import BaseError
from fastapi.responses import PlainTextResponse, UJSONResponse
from starlette.exceptions import ExceptionMiddleware
from kh_common.config.constants import environment
from kh_common.exceptions import jsonErrorHandler
from fastapi import FastAPI, Request
from typing import Iterable


def ServerApp(
	auth: bool = True,
	auth_required: bool = True,
	cors: bool = True,
	allowed_hosts: Iterable[str] = ['localhost', '127.0.0.1', '*.kheina.com', 'kheina.com'],
	allowed_origins: Iterable[str] = ['localhost', '127.0.0.1', 'dev.kheina.com', 'kheina.com'],
	allowed_methods: Iterable[str] = ['GET', 'POST'],
	max_age: int = 86400,
	allowed_headers: Iterable[str] = [
		'accept',
		'accept-language',
		'authorization',
		'cache-control',
		'content-encoding',
		'content-language',
		'content-length',
		'content-security-policy',
		'content-type',
		'cookie',
		'host',
		'location',
		'referer',
		'referrer-policy',
		'set-cookie',
		'user-agent',
		'www-authenticate',
		'x-frame-options',
		'x-xss-protection',
	],
	exposed_headers: Iterable[str] = [
		'authorization',
		'cache-control',
		'content-type',
		'cookie',
		'set-cookie',
		'www-authenticate',
	],
) -> FastAPI :
	app = FastAPI()
	app.add_middleware(ExceptionMiddleware, handlers={ Exception: jsonErrorHandler }, debug=False)
	app.add_exception_handler(BaseError, jsonErrorHandler)

	allowed_protocols = ['http', 'https'] if environment.is_local() else ['https']

	if cors :
		app.add_middleware(
			KhCorsMiddleware,
			allowed_origins = set(allowed_origins),
			allowed_protocols = set(allowed_protocols),
			allowed_headers = allowed_headers,
			allowed_methods = allowed_methods,
			exposed_headers = exposed_headers,
			max_age = max_age,
		)

	if allowed_hosts :
		app.add_middleware(TrustedHostMiddleware, allowed_hosts=set(allowed_hosts))

	if auth :
		app.add_middleware(KhAuthMiddleware, required=auth_required)

	return app
