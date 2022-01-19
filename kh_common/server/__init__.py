from starlette.types import ASGIApp, Receive, Send, Scope as request_scope
from starlette.middleware.trustedhost import TrustedHostMiddleware
from kh_common.server.middleware import CustomHeaderMiddleware
from kh_common.server.middleware.auth import KhAuthMiddleware
from kh_common.server.middleware.cors import KhCorsMiddleware
from kh_common.server.middleware.avro import AvroMiddleware
from kh_common.exceptions.base_error import BaseError
from starlette.exceptions import ExceptionMiddleware
from fastapi.responses import JSONResponse, Response
from kh_common.config.constants import environment
from kh_common.exceptions import jsonErrorHandler
# from kh_common.caching import SimpleCache
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Callable, Iterable, Type


from fastapi.routing import APIRoute, run_endpoint_function, serialize_response


NoContentResponse = Response(None, status_code=204)


def ServerApp(
	auth: bool = True,
	auth_required: bool = True,
	cors: bool = True,
	max_age: int = 86400,
	custom_headers: bool = True,
	allowed_hosts: Iterable[str] = [
		'localhost',
		'127.0.0.1',
		'*.kheina.com',
		'kheina.com',
	],
	allowed_origins: Iterable[str] = [
		'localhost',
		'127.0.0.1',
		'dev.kheina.com',
		'kheina.com',
	],
	allowed_methods: Iterable[str] = [
		'GET',
		'POST',
	],
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
	app = FastAPI(default_response_class=AvroJsonResponse)
	app.router.route_class = AvroRoute
	app.add_middleware(ExceptionMiddleware, handlers={ Exception: jsonErrorHandler }, debug=False)
	app.add_exception_handler(BaseError, jsonErrorHandler)

	allowed_protocols = ['http', 'https'] if environment.is_local() else ['https']

	if custom_headers :
		app.middleware('http')(CustomHeaderMiddleware)

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


from kh_common.avro import AvroSerializer


class AvroJsonResponse(JSONResponse) :

	# items are written to the cache in the form of type: writer
	_writer_cache_ = { }

	def __init__(self, serializable_body: dict, model: BaseModel, *args, **kwargs) :
		super().__init__(serializable_body, *args, **kwargs)
		self._model = model


	async def __call__(self, scope: request_scope, receive: Receive, send: Send) :
		request: Request = Request(scope, receive, send)

		if 'avro/binary' in request.headers.get('accept') :
			serializer: AvroSerializer = AvroSerializer(type(self._model))
			self.body = serializer(self._model)
			self.headers.update({
				'content-length': str(len(self.body)),
				'content-type': 'avro/binary',
			})

		await super().__call__(scope, receive, send)


from typing import Optional, Union, Type, Any, Dict
from fastapi.dependencies.models import Dependant
from fastapi.datastructures import DefaultPlaceholder
import asyncio
from fastapi import params
from fastapi.encoders import DictIntStrAny, SetIntStr
from pydantic.fields import ModelField, Undefined
import json
from fastapi.exceptions import RequestValidationError
from pydantic.error_wrappers import ErrorWrapper
from starlette.exceptions import HTTPException
from fastapi.dependencies.utils import solve_dependencies
import email.message


class AvroRoute(APIRoute) :

	def get_route_handler(self) -> Callable :
		dependant: Dependant = self.dependant
		body_field: Optional[ModelField] = self.body_field
		status_code: Optional[int] = self.status_code
		response_class: Union[Type[Response], DefaultPlaceholder] = self.response_class
		response_field: Optional[ModelField] = self.secure_cloned_response_field
		response_model_include: Optional[Union[SetIntStr, DictIntStrAny]] = self.response_model_include
		response_model_exclude: Optional[Union[SetIntStr, DictIntStrAny]] = self.response_model_exclude
		response_model_by_alias: bool = self.response_model_by_alias
		response_model_exclude_unset: bool = self.response_model_exclude_unset
		response_model_exclude_defaults: bool = self.response_model_exclude_defaults
		response_model_exclude_none: bool = self.response_model_exclude_none
		dependency_overrides_provider: Optional[Any] = self.dependency_overrides_provider

		assert dependant.call is not None, "dependant.call must be a function"
		is_coroutine = asyncio.iscoroutinefunction(dependant.call)
		is_body_form = body_field and isinstance(body_field.field_info, params.Form)
		if isinstance(response_class, DefaultPlaceholder):
			actual_response_class: Type[Response] = response_class.value
		else:
			actual_response_class = response_class

		async def app(request: Request) -> Response:
			try:
				body: Any = None
				if body_field:
					if is_body_form:
						body = await request.form()
					else:
						body_bytes = await request.body()
						if body_bytes:
							json_body: Any = Undefined
							content_type_value = request.headers.get("content-type")
							if not content_type_value:
								json_body = await request.json()
							else:
								message = email.message.Message()
								message["content-type"] = content_type_value
								if message.get_content_maintype() == "application":
									subtype = message.get_content_subtype()
									if subtype == "json" or subtype.endswith("+json"):
										json_body = await request.json()
							if json_body != Undefined:
								body = json_body
							else:
								body = body_bytes
			except json.JSONDecodeError as e:
				raise RequestValidationError([ErrorWrapper(e, ("body", e.pos))], body=e.doc)
			except Exception as e:
				raise HTTPException(
					status_code=400, detail="There was an error parsing the body"
				) from e
			solved_result = await solve_dependencies(
				request=request,
				dependant=dependant,
				body=body,
				dependency_overrides_provider=dependency_overrides_provider,
			)
			values, errors, background_tasks, sub_response, _ = solved_result
			if errors:
				raise RequestValidationError(errors, body=body)
			else:
				raw_response = await run_endpoint_function(
					dependant=dependant, values=values, is_coroutine=is_coroutine
				)

				if isinstance(raw_response, Response):
					if raw_response.background is None:
						raw_response.background = background_tasks
					return raw_response
				response_data = await serialize_response(
					field=response_field,
					response_content=raw_response,
					include=response_model_include,
					exclude=response_model_exclude,
					by_alias=response_model_by_alias,
					exclude_unset=response_model_exclude_unset,
					exclude_defaults=response_model_exclude_defaults,
					exclude_none=response_model_exclude_none,
					is_coroutine=is_coroutine,
				)
				response_args: Dict[str, Any] = {"background": background_tasks}
				# If status_code was set, use it, otherwise use the default from the
				# response class, in the case of redirect it's 307
				if status_code is not None:
					response_args["status_code"] = status_code
				response = actual_response_class(response_data, model=raw_response, **response_args)
				response.headers.raw.extend(sub_response.headers.raw)
				if sub_response.status_code:
					response.status_code = sub_response.status_code
				return response

		return app
