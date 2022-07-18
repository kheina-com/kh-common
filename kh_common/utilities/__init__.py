from collections import OrderedDict
from typing import Any, Iterable
from math import ceil
from time import time


def __clear_cache__(cache: OrderedDict, t=time) :
	now: float = t()

	try :
		while True :
			cache_key = next(cache.__iter__())
			if cache[cache_key][0] >= now : break
			del cache[cache_key]

	except StopIteration :
		pass


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


def flatten(it: Iterable[Any]) -> Iterable[Any] :
	if isinstance(it, str) :
		yield it
		return

	try :
		for i in (it.values() if isinstance(it, dict) else it) :
			yield from flatten(i)

	except TypeError :
		yield it


def int_to_bytes(integer: int) -> bytes :
	return integer.to_bytes(ceil(integer.bit_length() / 8), 'big')


def int_from_bytes(bytestring: bytes) -> int :
	return int.from_bytes(bytestring, 'big')
