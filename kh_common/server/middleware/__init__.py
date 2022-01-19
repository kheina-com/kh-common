from kh_common.config.repo import short_hash


async def CustomHeaderMiddleware(request, call_next) :
	response = await call_next(request)
	response.headers.update({
		'kh-hash': short_hash,
		# 'kh-service': name,
	})
	return response
