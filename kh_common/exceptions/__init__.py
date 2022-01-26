from kh_common.exceptions.base_error import BaseError
from kh_common.server.avro import AvroJsonResponse
from kh_common.logging import getLogger, Logger
from fastapi.requests import Request
from kh_common.models import Error
from typing import Dict, Union
from uuid import UUID, uuid4


logger: Logger = getLogger()


def jsonErrorHandler(request: Request, e: Exception) -> AvroJsonResponse :
	status: int = getattr(e, 'status', 500)
	refid: UUID = getattr(e, 'refid', uuid4())
	error: str

	if isinstance(e, BaseError) :
		error = f'{e.__class__.__name__}: {e}'

	else :
		logger.error({
			'status': status,
			'refid': refid.hex,
		}, exc_info=e)
		error = 'Internal Server Error'

	return AvroJsonResponse(
		{
			'status': status,
			'error': error,
			'refid': refid.hex,
		},
		Error(
			status=status,
			error=error,
			refid=refid.bytes,
		),
		# optimize: we still need to retrieve this value after it's been set by the router
		handshake=None,
		error=True,
		status_code=status,
	)
