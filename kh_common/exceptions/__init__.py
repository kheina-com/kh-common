from kh_common.exceptions.base_error import BaseError
from kh_common.logging import getLogger, Logger
from kh_common.server import AvroJsonResponse
from kh_common.models import Error
from typing import Dict, Union
from fastapi import Request
from uuid import uuid4


logger: Logger = getLogger()


def jsonErrorHandler(request: Request, e: Exception) -> AvroJsonResponse :
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

	return AvroJsonResponse(
		error,
		Error,
		handshake=None,
		status_code=status,
	)
