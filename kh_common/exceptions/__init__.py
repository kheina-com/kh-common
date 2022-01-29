from kh_common.exceptions.base_error import BaseError
from kh_common.avro.routing import AvroJsonResponse
from kh_common.models import Error, ValidationError
from kh_common.logging import getLogger, Logger
from kh_common.avro import AvroSerializer
from fastapi.requests import Request
from uuid import UUID, uuid4
from typing import Union


logger: Logger = getLogger()
serializer: AvroSerializer = AvroSerializer(Union[Error, ValidationError])


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
		model=Error(
			status=status,
			error=error,
			refid=refid.bytes,
		),
		serializer=serializer,
		error=True,
		status_code=status,
	)
