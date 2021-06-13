from inspect import FullArgSpec, getfullargspec, iscoroutinefunction
from typing import Any, Callable, Dict, Iterable, Set, Tuple
from kh_common.exceptions.base_error import BaseError
from kh_common.logging import getLogger, Logger
from uuid import UUID, uuid4
from functools import wraps
from enum import Enum


logger: Logger = getLogger()


class HttpError(BaseError) :
	def __init__(self, message: str, *args:Tuple[Any], status:int=500, **kwargs: Dict[str, Any]) -> None :
		super().__init__(message, *args, **kwargs)
		self.status = status


class NotFound(HttpError) :
	def __init__(self, message: str, *args:Tuple[Any], **kwargs: Dict[str, Any]) -> None :
		super().__init__(message, *args, status=404, **kwargs)


class BadRequest(HttpError) :
	def __init__(self, message: str, *args:Tuple[Any], **kwargs: Dict[str, Any]) -> None :
		super().__init__(message, *args, status=400, **kwargs)


class Unauthorized(HttpError) :
	def __init__(self, message: str, *args:Tuple[Any], **kwargs: Dict[str, Any]) -> None :
		super().__init__(message, *args, status=401, **kwargs)


class Forbidden(HttpError) :
	def __init__(self, message: str, *args:Tuple[Any], **kwargs: Dict[str, Any]) -> None :
		super().__init__(message, *args, status=403, **kwargs)


class UnsupportedMedia(HttpError) :
	def __init__(self, message: str, *args:Tuple[Any], **kwargs: Dict[str, Any]) -> None :
		super().__init__(message, *args, status=415, **kwargs)


class UnprocessableEntity(HttpError) :
	def __init__(self, message: str, *args:Tuple[Any], **kwargs: Dict[str, Any]) -> None :
		super().__init__(message, *args, status=422, **kwargs)


class Conflict(HttpError) :
	def __init__(self, message: str, *args:Tuple[Any], **kwargs: Dict[str, Any]) -> None :
		super().__init__(message, *args, status=409, **kwargs)


class InternalServerError(HttpError) :
	pass


class ResponseNotOk(HttpError) :
	pass


class BadOrMalformedResponse(HttpError) :
	pass


def HttpErrorHandler(message: str, exclusions: Iterable[str] = ['self'], handlers: Dict[type, Tuple[type, str]] = { }) -> Callable :
	"""
	raises internal server error from any unexpected errors
	f'an unexpected error occurred while {message}.'
	"""

	exclusions: Set[str] = set(exclusions)

	def decorator(func: Callable) -> Callable :

		arg_spec: FullArgSpec = getfullargspec(func)

		if iscoroutinefunction(func) :
			@wraps(func)
			async def wrapper(*args: Tuple[Any], **kwargs:Dict[str, Any]) -> Any :
				try :
					return await func(*args, **kwargs)

				except HttpError :
					raise

				except Exception as e :
					for cls in type(e).__mro__ :
						if cls in handlers :
							Error, custom_message = handlers[cls]
							raise Error(custom_message)

					kwargs.update(zip(arg_spec.args, args))
					kwargs['refid']: UUID = uuid4().hex

					logdata = {
						key: kwargs[key]
						for key in kwargs.keys() - exclusions
					}
					logger.exception({ 'params': logdata })

					raise InternalServerError(f'an unexpected error occurred while {message}.', logdata=logdata)

		else :
			@wraps(func)
			def wrapper(*args: Tuple[Any], **kwargs:Dict[str, Any]) -> Any :
				try :
					return func(*args, **kwargs)

				except HttpError :
					raise

				except Exception as e :
					for cls in type(e).__mro__ :
						if cls in handlers :
							Error, custom_message = handlers[cls]
							raise Error(custom_message)

					kwargs.update(zip(arg_spec.args, args))
					kwargs['refid']: UUID = uuid4().hex

					logdata = {
						key: kwargs[key]
						for key in kwargs.keys() - exclusions
					}
					logger.exception({ 'params': logdata })

					raise InternalServerError(f'an unexpected error occurred while {message}.', logdata=logdata)

		return wrapper

	return decorator
