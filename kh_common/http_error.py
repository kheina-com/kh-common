class HttpError(Exception) :
	def __init__(self, message, status=500, logdata={ }) :
		super().__init__(message)
		self.status = status
		self.logdata = logdata

class NotFound(HttpError) :
	def __init__(self, message, *args, **kwargs) :
		super().__init__(message, *args, status=404, **kwargs)

class BadRequest(HttpError) :
	def __init__(self, message, *args, **kwargs) :
		super().__init__(message, *args, status=400, **kwargs)

class Unauthorized(HttpError) :
	def __init__(self, message, *args, **kwargs) :
		super().__init__(message, *args, status=401, **kwargs)

class Forbidden(HttpError) :
	def __init__(self, message, *args, **kwargs) :
		super().__init__(message, *args, status=403, **kwargs)

class UnsupportedMedia(HttpError) :
	def __init__(self, message, *args, **kwargs) :
		super().__init__(message, *args, status=415, **kwargs)

class InternalServerError(HttpError) :
	pass

class ResponseNotOk(HttpError) :
	pass

class BadOrMalformedResponse(HttpError) :
	pass
