from typing import Any, Awaitable, Callable, Coroutine, Dict, List, Optional, Sequence, Type, Union

from fastapi import FastAPI
from fastapi.datastructures import Default
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.logger import logger
from fastapi.params import Depends
from fastapi.routing import APIRoute, APIRouter
from fastapi.utils import generate_unique_id
from starlette.datastructures import State
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute
from starlette.types import ASGIApp

from kh_common.avro.routing import AvroJsonResponse, AvroRouter


class AvroFastAPI(FastAPI) :

	def __init__(
		self: 'AvroFastAPI',
		*,
		debug: bool = False,
		routes: Optional[List[BaseRoute]] = None,
		title: str = 'Avro FastAPI',
		description: str = '',
		version: str = '0.1.0',
		openapi_url: Optional[str] = '/openapi.json',
		openapi_tags: Optional[List[Dict[str, Any]]] = None,
		servers: Optional[List[Dict[str, Union[str, Any]]]] = None,
		dependencies: Optional[Sequence[Depends]] = None,
		default_response_class: Type[Response] = Default(AvroJsonResponse),
		docs_url: Optional[str] = '/docs',
		redoc_url: Optional[str] = '/redoc',
		swagger_ui_oauth2_redirect_url: Optional[str] = '/docs/oauth2-redirect',
		swagger_ui_init_oauth: Optional[Dict[str, Any]] = None,
		middleware: Optional[Sequence[Middleware]] = None,
		exception_handlers: Optional[
			Dict[
				Union[int, Type[Exception]],
				Callable[[Request, Any], Coroutine[Any, Any, Response]],
			]
		] = None,
		on_startup: Optional[Sequence[Callable[[], Any]]] = None,
		on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,
		terms_of_service: Optional[str] = None,
		contact: Optional[Dict[str, Union[str, Any]]] = None,
		license_info: Optional[Dict[str, Union[str, Any]]] = None,
		openapi_prefix: str = '',
		root_path: str = '',
		root_path_in_servers: bool = True,
		responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
		callbacks: Optional[List[BaseRoute]] = None,
		deprecated: Optional[bool] = None,
		include_in_schema: bool = True,
		swagger_ui_parameters: Optional[Dict[str, Any]] = None,
		generate_unique_id_function: Callable[[APIRoute], str] = Default(generate_unique_id),
		router_class: Type[APIRouter] = AvroRouter,
		**extra: Any,
	) -> None :
		self._debug: bool = debug
		self.title = title
		self.description = description
		self.version = version
		self.terms_of_service = terms_of_service
		self.contact = contact
		self.license_info = license_info
		self.openapi_url = openapi_url
		self.openapi_tags = openapi_tags
		self.root_path_in_servers = root_path_in_servers
		self.docs_url = docs_url
		self.redoc_url = redoc_url
		self.swagger_ui_oauth2_redirect_url = swagger_ui_oauth2_redirect_url
		self.swagger_ui_init_oauth = swagger_ui_init_oauth
		self.swagger_ui_parameters = swagger_ui_parameters
		self.servers = servers or []
		self.extra = extra
		self.openapi_version = "3.0.2"
		self.openapi_schema: Optional[Dict[str, Any]] = None
		if self.openapi_url:
			assert self.title, "A title must be provided for OpenAPI, e.g.: 'My API'"
			assert self.version, "A version must be provided for OpenAPI, e.g.: '2.1.0'"
		# TODO: remove when discarding the openapi_prefix parameter
		if openapi_prefix:
			logger.warning(
				'"openapi_prefix" has been deprecated in favor of "root_path", which '
				"follows more closely the ASGI standard, is simpler, and more "
				"automatic. Check the docs at "
				"https://fastapi.tiangolo.com/advanced/sub-applications/"
			)
		self.root_path = root_path or openapi_prefix
		self.state: State = State()
		self.dependency_overrides: Dict[Callable[..., Any], Callable[..., Any]] = {}
		self.router: APIRouter = router_class(
			routes=routes,
			dependency_overrides_provider=self,
			on_startup=on_startup,
			on_shutdown=on_shutdown,
			default_response_class=default_response_class,
			dependencies=dependencies,
			callbacks=callbacks,
			deprecated=deprecated,
			include_in_schema=include_in_schema,
			responses=responses,
			generate_unique_id_function=generate_unique_id_function,
		)
		self.exception_handlers: Dict[
			Any, Callable[[Request, Any], Union[Response, Awaitable[Response]]]
		] = ({} if exception_handlers is None else dict(exception_handlers))
		self.exception_handlers.setdefault(HTTPException, http_exception_handler)
		self.exception_handlers.setdefault(
			RequestValidationError, request_validation_exception_handler
		)

		self.user_middleware: List[Middleware] = (
			[] if middleware is None else list(middleware)
		)
		self.middleware_stack: ASGIApp = self.build_middleware_stack()
		self.setup()
