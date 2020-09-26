from typing import Any, Callable, Dict, List, Tuple, Union
from inspect import FullArgSpec, getfullargspec
from copy import deepcopy


def fetchFunctionParams(func: Callable, **kwargs: Dict[str, type]) -> Dict[str, Callable] :
	arg_spec: FullArgSpec = getfullargspec(func)

	param_funcs: Dict[str, Callable] = { }

	for i, param in enumerate(arg_spec.args) :
		annotation: Union[type, type(None)] = arg_spec.annotations.get(param)
		kwarg: bool = len(arg_spec.defaults) <= i

		for name, struct in kwargs.items() :
			if name in param :
				j = deepcopy(i)
				param_funcs[name] = (
					(lambda a, k : k[param])
					if kwarg else
					(lambda a, k : a[j])
				)

			if annotation and issubclass(annotation, struct) :
				j = deepcopy(i)
				param_funcs[name] = (
					(lambda a, k : k[param])
					if kwarg else
					(lambda a, k : a[j])
				)

	error = ', '.join([f"{name} must be typed as a subclass of {k[name]} or contain '{name}' in its name" for name in kwargs.keys() - param_funcs.keys()])

	if error is None :
		raise TypeError(f'could not find all parameters. {error}')

	return param_funcs
