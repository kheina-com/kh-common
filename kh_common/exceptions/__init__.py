from typing import Any, Callable, Dict, List, Tuple, Union
from kh_common.exceptions.http_error import HttpError
from kh_common.config.constants import environment
from kh_common import getFullyQualifiedClassName
from kh_common.logging import getLogger, Logger
from starlette.responses import UJSONResponse
from traceback import format_tb
from types import TracebackType
from fastapi import Request
from sys import exc_info
from uuid import uuid4


logger: Logger = getLogger()


def jsonErrorHandler(request: Request, e: Exception) :
	status: int = getattr(e, 'status', 500)

	error: Dict[str, Union[str, int]] = {
		'status': status,
		'refid': getattr(e, 'refid', uuid4().hex),
	}

	if isinstance(e, HttpError) :
		error['error']: str = f'{status} {e.__class__.__name__}: {e}'

	else :
		logger.exception({
			'error': f'{status} {getFullyQualifiedClassName(e)}: {e}',
			**error,
			**getattr(e, 'logdata', { }),
		})
		error['error']: str = f'500 Internal Server Error: {e}'

	return UJSONResponse(
		error,
		status_code=status,
	)
