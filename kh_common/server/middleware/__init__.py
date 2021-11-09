from kh_common.config.repo import short_hash
from fastapi import Request


async def CustomHeaderMiddleware(request: Request, call_next):
	response = await call_next(request)
	response.headers.update({
		'kh-hash': short_hash,
	})
	return response
