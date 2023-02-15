from typing import Dict, Union
from uuid import uuid4

from aiohttp import ClientError
from fastapi import Request
from fastapi.responses import UJSONResponse

from ..logging import Logger, getLogger
from .base_error import BaseError
from .http_error import BadGateway


logger: Logger = getLogger()


def jsonErrorHandler(request: Request, e: Exception) -> UJSONResponse :
	status: int = getattr(e, 'status', 500)

	error: Dict[str, Union[str, int]] = {
		'status': status,
		'refid': getattr(e, 'refid', uuid4()).hex,
	}

	if isinstance(e, BaseError) :
		error['error'] = f'{e.__class__.__name__}: {e}'

	elif isinstance(e, ClientError) :
		error['error'] = f'{BadGateway.__name__}: received an invalid response from an upstream server.'
		status = error['status'] = BadGateway.status
		logger.error(error, exc_info=e)

	else :
		logger.error(error, exc_info=e)
		error['error'] = 'Internal Server Error'

	return UJSONResponse(
		error,
		status_code=status,
	)
