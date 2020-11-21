from kh_common.exceptions.http_error import HttpError
from kh_common import getFullyQualifiedClassName
from kh_common.logging import getLogger, Logger
from starlette.responses import UJSONResponse
from traceback import format_tb
from types import TracebackType
from typing import Dict, Union
from fastapi import Request
from sys import exc_info
from uuid import uuid4


logger: Logger = getLogger()


def jsonErrorHandler(request: Request, e: Exception) -> UJSONResponse :
	status: int = getattr(e, 'status', 500)

	error: Dict[str, Union[str, int]] = {
		'status': status,
		'refid': getattr(e, 'refid', uuid4().hex),
	}

	if isinstance(e, HttpError) :
		error['error']: str = f'{e.__class__.__name__}: {e}'

	else :
		logger.error(error, exc_info=e)
		error['error']: str = 'Internal Server Error'

	return UJSONResponse(
		error,
		status_code=status,
	)
