from kh_common.exceptions.base_error import BaseError
from kh_common.logging import getLogger, Logger
from fastapi.requests import Request
from kh_common.models import Error
from uuid import UUID, uuid4
from kh_common.avro.routing import AvroJsonResponse


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
		serializable_body={
			'status': status,
			'error': error,
			'refid': refid.hex,
		},
		model=Error(
			status=status,
			error=error,
			refid=refid.bytes,
		),
		error=True,
		status_code=status,
	)
