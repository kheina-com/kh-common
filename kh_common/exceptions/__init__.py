from kh_common.utilities import getFullyQualifiedClassName
from kh_common.exceptions.base_error import BaseError
from kh_common.logging import getLogger, Logger
from fastapi.responses import UJSONResponse
from typing import Dict, Union
from fastapi import Request
from uuid import uuid4


logger: Logger = getLogger()


def jsonErrorHandler(request: Request, e: Exception) -> UJSONResponse :
	status: int = getattr(e, 'status', 500)

	error: Dict[str, Union[str, int]] = {
		'status': status,
		'refid': getattr(e, 'refid', uuid4()).hex,
	}

	if isinstance(e, BaseError) :
		error['error'] = f'{e.__class__.__name__}: {e}'

	else :
		logger.error(error, exc_info=e)
		error['error'] = 'Internal Server Error'

	return UJSONResponse(
		error,
		status_code=status,
	)
