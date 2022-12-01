from typing import Union
from uuid import UUID, uuid4

from aiohttp import ClientError
from fastapi import Request
from fastapi.requests import Request

from kh_common.avro.routing import AvroJsonResponse
from kh_common.avro.serialization import AvroSerializer
from kh_common.exceptions.base_error import BaseError
from kh_common.exceptions.http_error import BadGateway
from kh_common.logging import Logger, getLogger
from kh_common.models import Error, ValidationError

logger: Logger = getLogger()
serializer: AvroSerializer = AvroSerializer(Union[Error, ValidationError])


def jsonErrorHandler(_: Request, e: Exception) -> AvroJsonResponse :
	status: int = getattr(e, 'status', 500)
	refid: UUID = getattr(e, 'refid', uuid4())
	error: str

	if isinstance(e, BaseError) :
		error = f'{e.__class__.__name__}: {e}'

	elif isinstance(e, ClientError) :
		error = f'{BadGateway.__name__}: received an invalid response from an upstream server.'
		status = BadGateway.status
		logger.error({
			'error': error,
			'status': status,
			'refid': refid.hex,
		}, exc_info=e)

	else :
		error = 'Internal Server Error'
		logger.error({
			'error': error,
			'status': status,
			'refid': refid.hex,
		}, exc_info=e)

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
