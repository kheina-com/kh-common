from kh_common.exceptions.base_error import BaseError
from typing import Any, Dict, Tuple


class HttpError(BaseError) :
	def __init__(self, message: str, *args:Tuple[Any], status:int=500, **kwargs: Dict[str, Any]) -> type(None) :
		super().__init__(message, *args, **kwargs)
		self.status = status


class NotFound(HttpError) :
	def __init__(self, message: str, *args:Tuple[Any], **kwargs: Dict[str, Any]) -> type(None) :
		super().__init__(message, *args, status=404, **kwargs)


class BadRequest(HttpError) :
	def __init__(self, message: str, *args:Tuple[Any], **kwargs: Dict[str, Any]) -> type(None) :
		super().__init__(message, *args, status=400, **kwargs)


class Unauthorized(HttpError) :
	def __init__(self, message: str, *args:Tuple[Any], **kwargs: Dict[str, Any]) -> type(None) :
		super().__init__(message, *args, status=401, **kwargs)


class Forbidden(HttpError) :
	def __init__(self, message: str, *args:Tuple[Any], **kwargs: Dict[str, Any]) -> type(None) :
		super().__init__(message, *args, status=403, **kwargs)


class UnsupportedMedia(HttpError) :
	def __init__(self, message: str, *args:Tuple[Any], **kwargs: Dict[str, Any]) -> type(None) :
		super().__init__(message, *args, status=415, **kwargs)


class InternalServerError(HttpError) :
	pass


class ResponseNotOk(HttpError) :
	pass


class BadOrMalformedResponse(HttpError) :
	pass
