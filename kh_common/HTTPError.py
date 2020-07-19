class HTTPError(Exception) :
	def __init__(self, message, status=500, logdata={ }) :
		super().__init__(message)
		self.status = status
		self.logdata = logdata

class NotFound(HTTPError) :
	def __init__(self, message, *args, **kwargs) :
		super().__init__(message, *args, status=404, **kwargs)

class BadRequest(HTTPError) :
	def __init__(self, message, *args, **kwargs) :
		super().__init__(message, *args, status=400, **kwargs)

class Unauthorized(HTTPError) :
	def __init__(self, message, *args, **kwargs) :
		super().__init__(message, *args, status=401, **kwargs)

class Forbidden(HTTPError) :
	def __init__(self, message, *args, **kwargs) :
		super().__init__(message, *args, status=403, **kwargs)

class UnsupportedMedia(HTTPError) :
	def __init__(self, message, *args, **kwargs) :
		super().__init__(message, *args, status=415, **kwargs)

class InternalServerError(HTTPError) :
	pass

class ResponseNotOk(HTTPError) :
	pass

class BadOrMalformedResponse(HTTPError) :
	pass
