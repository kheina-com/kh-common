from kh_common.exceptions.http_error import BadRequest, InternalServerError
from typing import Any, Callable, Dict, List, Tuple, Union
from kh_common.config.constants import environment
from kh_common import getFullyQualifiedClassName
from kh_common.logging import getLogger, Logger
from inspect import FullArgSpec, getfullargspec
from starlette.responses import UJSONResponse
from starlette.requests import Request
from traceback import format_tb
from types import TracebackType
from functools import wraps
from sys import exc_info
from uuid import uuid4


logger = getLogger()


def _jsonErrorHandler(req: Request, log:bool=False, stacktrace:bool=False) :
	e: ConnectionException
	traceback: TracebackType
	e, traceback = exc_info()[1:]
	status: int = getattr(e, 'status', 500)

	error: Dict[str, Union[str, int]] = {
		'error': f'{status} {getFullyQualifiedClassName(e)}: {e}',
		'status': status,
		'method': req.method,
		'url': str(req.url),
		'refid': getattr(e, 'refid', uuid4().hex),
	}

	traceback: List[str] = format_tb(traceback)

	if stacktrace :
		error['stacktrace']: List[str] = traceback

	if log :
		logger.error({
			**error,
			'stacktrace': traceback,
			**getattr(e, 'logdata', { }),
		})

	return UJSONResponse(
		error,
		status_code=status,
	)


def jsonErrorHandler(func: Callable) -> Callable :
	request_index: Union[int, type(None)] = None

	for i, (k, v) in enumerate(func.__annotations__.items()) :
		if 'req' in k.lower() :
			request_index = i

		if issubclass(v, Request) :
			request_index = i

	if request_index is None :
		raise TypeError("request object must be typed as a subclass of starlette.requests.Request or contain 'req' in its name")

	@wraps(func)
	async def wrapper(*args: Tuple[Any], **kwargs:Dict[str, Any]) -> Any :
		request: Request = args[request_index]
		try :
			return await func(*args, **kwargs)
		except :
			return _jsonErrorHandler(request, stacktrace=(environment == 'local'))

	return wrapper


def GenericErrorHandler(message: str) -> Callable :
	"""
	raises internal server error from any unexpected errors
	f'an unexpected error occurred while {message}.'
	"""

	def decorator(func: Callable) -> Callable :

		arg_spec: FullArgSpec = getfullargspec(func)

		@wraps(func)
		def wrapper(*args: Tuple[Any], **kwargs:Dict[str, Any]) -> Any :
			request: Request = args[request_index]
			try :
				return func(*args, **kwargs)

			except HttpError :
				raise

			except :
				kwargs.update(zip(arg_spec.args, args))
				kwargs['refid']: str = uuid4().hex
				logger.exception(kwargs)
				raise InternalServerError(f'an unexpected error occurred while {message}.', logdata=kwargs)

		return wrapper
	
	return decorator


def checkJsonKeys(json_body: Dict[str, Any], keys: List[str]) :
	missing_keys = [key for key in keys if key not in json_body]

	if missing_keys :
		raise BadRequest(f'request body is missing required keys: {", ".join(missing_keys)}.', keys=missing_keys)
