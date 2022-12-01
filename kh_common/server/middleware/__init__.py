from typing import Dict

from fastapi import Request

from kh_common.config.repo import short_hash


HeadersToSet: Dict[str, str] = {
	'kh-hash': short_hash,
}


async def CustomHeaderMiddleware(request: Request, call_next):
	response = await call_next(request)
	response.headers.update(HeadersToSet)
	return response
