from kh_common.exceptions.http_error import BadRequest
from typing import Any, Callable, Dict, Tuple, Union
from pydantic.error_wrappers import ValidationError
from starlette.requests import Request
from pydantic import BaseModel
from functools import wraps


def validatedJson(func: Callable) -> Callable :
	request_index: Union[int, type(None)] = None
	request_object: Union[type, type(None)] = None

	for i, v in enumerate(func.__annotations__.keys()) :
		if 'req' in v.lower() :
			request_index = i
			request_object = func.__annotations__[v]

	if request_index is None :
		raise TypeError("request object must contain 'req' in its name")

	@wraps(func)
	async def wrapper(*args: Tuple[Any], **kwargs:Dict[str, Any]) -> Any :
		args = list(args)
		request: Request = args[request_index]

		data = await request.json()

		try :
			args[request_index]: request_object = request_object(**data)
		
		except ValidationError as e :
			raise BadRequest(
				'json input invalid: ' +
				', '.join([
					', '.join(d['loc']) +
					(d['msg'][5:] if d['msg'].startswith('value') else d['msg'])
					for d in e.errors()
				])
			)

		return await func(*args, **kwargs)
	return wrapper
