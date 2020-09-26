from typing import Any, Callable, Dict, List, Tuple, Union
from inspect import FullArgSpec, getfullargspec


def fetchFunctionParams(func: Callable, **kwargs: Dict[str, type]) -> Dict[str, Callable] :
	arg_spec: FullArgSpec = getfullargspec(func)

	param_funcs: Dict[str, Callable] = { }

	for i, param in enumerate(arg_spec.args) :
		annotation: Union[type, type(None)] = arg_spec.annotations.get(param)
		kwarg: bool = len(arg_spec.defaults) > i

		

		if issubclass(v, Request) :
			request_index = i

	if get_request is None :
		raise TypeError("request object must be typed as a subclass of starlette.requests.Request or contain 'req' in its name")

