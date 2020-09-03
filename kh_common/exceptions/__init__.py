from kh_common import getFullyQualifiedClassName
from starlette.responses import UJSONResponse
from sys import exc_info
from uuid import uuid4


def jsonErrorHandler(req, logger) :
	e = exc_info()[1]
	status = getattr(e, 'status', 500)

	error = {
		'error': f'{status} {getFullyQualifiedClassName(e)}: {e}',
		'status': status,
		'method': req.method,
		'url': str(req.url),
		'uuid': getattr(e, 'uuid', uuid4().hex),
	}
	return UJSONResponse(
		error,
		status_code=status,
	)
