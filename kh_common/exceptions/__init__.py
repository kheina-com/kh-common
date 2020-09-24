from kh_common import getFullyQualifiedClassName
from starlette.responses import UJSONResponse
from starlette.requests import Request
from typing import Dict, List, Union
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
