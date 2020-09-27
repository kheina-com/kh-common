from typing import Any, Callable, Dict, Iterable, Set, Tuple
from kh_common.exceptions.base_error import BaseError
from inspect import FullArgSpec, getfullargspec
from kh_common.logging import getLogger, Logger
from functools import wraps
from uuid import uuid4
from enum import Enum


logger: Logger = getLogger()


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


def HttpErrorHandler(message: str, exclusions:Iterable[str]=['self']) -> Callable :
	"""
	raises internal server error from any unexpected errors
	f'an unexpected error occurred while {message}.'
	"""

	exclusions: Set[str] = set(exclusions)

	def decorator(func: Callable) -> Callable :

		arg_spec: FullArgSpec = getfullargspec(func)

		@wraps(func)
		def wrapper(*args: Tuple[Any], **kwargs:Dict[str, Any]) -> Any :
			try :
				return func(*args, **kwargs)

			except HttpError :
				raise

			except :
				kwargs.update(zip(arg_spec.args, args))
				kwargs['refid']: str = uuid4().hex
				logdata = {
					key: (kwargs[key].name if isinstance(kwargs[key], Enum) else kwargs[key])
					for key in kwargs.keys() - exclusions
				}
				logger.exception(logdata)
				raise InternalServerError(f'an unexpected error occurred while {message}.', logdata=logdata)

		return wrapper

	return decorator
