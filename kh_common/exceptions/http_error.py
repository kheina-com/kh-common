from inspect import FullArgSpec, getfullargspec, iscoroutinefunction
from typing import Any, Callable, Dict, Iterable, Set, Tuple, Type
from kh_common.exceptions.base_error import BaseError
from kh_common.logging import getLogger, Logger
from aiohttp import ClientError
from functools import wraps
from uuid import uuid4


logger: Logger = getLogger()


class HttpError(BaseError) :
	status: int = 500


class BadRequest(HttpError) :
	status: int = 400


class Unauthorized(HttpError) :
	status: int = 401


class Forbidden(HttpError) :
	status: int = 403


class NotFound(HttpError) :
	status: int = 404


class Conflict(HttpError) :
	status: int = 409


class UnsupportedMedia(HttpError) :
	status: int = 415


class UnprocessableEntity(HttpError) :
	status: int = 422


class BadGateway(HttpError) :
	status: int = 502


class ServiceUnavailable(HttpError) :
	status: int = 503


class InternalServerError(HttpError) :
	pass


class ResponseNotOk(HttpError) :
	pass


class BadOrMalformedResponse(HttpError) :
	pass


def HttpErrorHandler(message: str, exclusions: Iterable[str] = ['self'], handlers: Dict[Type[Exception], Tuple[Type[Exception], str]] = { }) -> Callable :
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
					refid: str = uuid4().hex

					logdata = {
						key: kwargs[key]
						for key in kwargs.keys() - exclusions
					}
					logger.exception({ 'params': logdata, 'refid': refid })

					if isinstance(e, ClientError) :
						raise BadGateway(
							f'{BadGateway.__name__}: received an invalid response from an upstream server while {message}.',
							refid = refid,
							logdata = logdata,
						)

					raise InternalServerError(
						f'an unexpected error occurred while {message}.',
						refid = refid,
						logdata = logdata,
					)

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
					refid: str = uuid4().hex

					logdata = {
						key: kwargs[key]
						for key in kwargs.keys() - exclusions
					}
					logger.exception({ 'params': logdata, 'refid': refid })

					if isinstance(e, ClientError) :
						raise BadGateway(
							f'{BadGateway.__name__}: received an invalid response from an upstream server while {message}.',
							refid = refid,
							logdata = logdata,
						)

					raise InternalServerError(
						f'an unexpected error occurred while {message}.',
						refid = refid,
						logdata = logdata,
					)

		return wrapper

	return decorator
