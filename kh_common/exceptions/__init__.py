from kh_common import getFullyQualifiedClassName
from starlette.responses import UJSONResponse
from traceback import format_tb
from sys import exc_info
from uuid import uuid4


def jsonErrorHandler(req, logger=None, stacktrace=False) :
	e, exc_tb = exc_info()[1:]
	status = getattr(e, 'status', 500)

	error = {
		'error': f'{status} {getFullyQualifiedClassName(e)}: {e}',
		'status': status,
		'method': req.method,
		'url': str(req.url),
		'uuid': getattr(e, 'uuid', uuid4().hex),
	}

	traceback = format_tb(exc_tb)

	if stacktrace :
		error['stacktrace'] = traceback

	if logger :
		logger.error({
			**error,
			'stacktrace': traceback,
			**getattr(e, 'logdata', { }),
		})

	return UJSONResponse(
		error,
		status_code=status,
	)
