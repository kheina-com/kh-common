__version__: str = '0.4.0'


def getFullyQualifiedClassName(obj: object) -> str :
	module = getattr(obj, '__module__', None)
	if module and module != str.__module__ :
		return f'{module}.{obj.__class__.__name__}'
	return obj.__class__.__name__


def stringSlice(string: str, start:str=None, end:str=None) -> str :
	if not string : return None
	assert start or end, 'start or end is required'
	start = string.rfind(start) + len(start) if start else None
	end = string.find(end) if end else None
	return string[start:end]


def flatten(it: Iterator[Any]) -> Iterator[Any] :
	if isinstance(it, (tuple, list, set)) :
		for i in it :
			yield from flatten(i)
	elif isinstance(it, dict) :
		for v in it.values() :
			yield from flatten(v)
	else :
		yield it
