__version__ = '0.2.6'


def getFullyQualifiedClassName(obj) :
	module = getattr(obj, '__module__', None)
	if module and module != str.__module__ :
		return f'{module}.{obj.__class__.__name__}'
	return obj.__class__.__name__

def stringSlice(string: str, start:str=None, end:str=None) :
	if not string : return None
	assert start or end, 'start or end is required'
	start = string.rfind(start) + 1 if start else None
	end = string.find(end) if end else None
	return string[start:end]
