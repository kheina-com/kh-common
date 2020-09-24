from typing import Any, Callable, Dict, List, Tuple, Union
from kh_common.exceptions.http_error import BadRequest
from kh_common import getFullyQualifiedClassName
from starlette.responses import UJSONResponse
from starlette.requests import Request
from kh_common.logging import Logger
from traceback import format_tb
from types import TracebackType
from sys import exc_info
from uuid import uuid4


def jsonErrorHandler(req: Request, logger:Union[Logger, type(None)]=None, stacktrace:bool=False) :
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

	if logger :
		logger.error({
			**error,
			'stacktrace': traceback,
			**getattr(e, 'logdata', { }),
		})

	return UJSONResponse(
		error,
		status_code=status,
	)


# PascalCase because these are technically classes
def JsonErrorHandler(request_index:int=0) -> Callable :
	# handles any errors occurring during request responses

	def decorator(func: Callable) -> Callable :
		async def wrapper(*args: Tuple[Any], **kwargs:Dict[str, Any]) -> Any :
			request: Request = args[request_index]
			try :
				return await func(*args, **kwargs)
			except :
				return jsonErrorHandler(request)
		return wrapper
	return decorator


def checkJsonKeys(json_body: Dict[str, Any], keys: List[str]) :
	missing_keys = [key for key in keys if key not in json_body]

	if missing_keys :
		raise BadRequest(f'request body is missing required keys: {", ".join(missing_keys)}.', keys=missing_keys)
