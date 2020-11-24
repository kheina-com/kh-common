from typing import Any, Callable, Dict, Hashable, Iterable, Tuple, Union
from inspect import FullArgSpec, getfullargspec, iscoroutinefunction
from collections import defaultdict
from enum import Enum, unique
from functools import wraps
from time import time


class CalcDict(dict) :

	def __init__(self, default: Callable[[Hashable], Any]) -> type(None) :
		self.default: Callable = default


	def setdefault(self, default: Callable[[Hashable], Any]) -> type(None) :
		self.default = default


	def __missing__(self, key: Hashable) -> Any:
		self[key] = self.default(key)
		return self[key]


_conversions: Dict[type, Callable] = {
	dict: lambda x : tuple((key, k[key]) for key in sorted(k.keys())),
	list: tuple,
}


def _convert_item(item: Any) -> Any :
	item_type = type(item)
	if isinstance(item, Iterable) :
		return _cache_stream(item)
	if item_type in _conversions :
		return _conversions[item_type](item)
	return item


def _cache_stream(stream: Iterable) :
	if isinstance(stream, dict) :
		return tuple((key, _convert_item(stream[key])) for key in sorted(stream.keys()))

	else :
		return tuple(map(_convert_item, stream))


# PascalCase because these are technically classes
def SimpleCache(TTL_seconds:float=0, TTL_minutes:float=0, TTL_hours:float=0, TTL_days:float=0) -> Callable :
	TTL: float = TTL_seconds + TTL_minutes / 60 + TTL_hours / 3600 + TTL_days / 86400
	del TTL_seconds, TTL_minutes, TTL_hours, TTL_days

	def decorator(func: Callable) -> Callable :
		if iscoroutinefunction(func) :
			@wraps(func)
			async def wrapper(*args: Tuple[Any], **kwargs:Dict[str, Any]) -> Any :
				now: float = time()
				if now > decorator.expire :
					decorator.expire = now + TTL
					decorator.data = await func(*args, **kwargs)
				return decorator.data

		else :
			@wraps(func)
			def wrapper(*args: Tuple[Any], **kwargs:Dict[str, Any]) -> Any :
				now: float = time()
				if now > decorator.expire :
					decorator.expire = now + TTL
					decorator.data = func(*args, **kwargs)
				return decorator.data

		return wrapper
	decorator.expire: float = 0
	decorator.data: Any = None
	return decorator


# PascalCase because these are technically classes
def ArgsCache(TTL_seconds:float=0, TTL_minutes:float=0, TTL_hours:float=0, TTL_days:float=0) -> Callable :
	TTL: float = TTL_seconds + TTL_minutes / 60 + TTL_hours / 3600 + TTL_days / 86400
	del TTL_seconds, TTL_minutes, TTL_hours, TTL_days

	def decorator(func: Callable) -> Callable :

		if iscoroutinefunction(func) :
			@wraps(func)
			async def wrapper(*args: Tuple[Any], **kwargs:Dict[str, Any]) -> Any :
				now: float = time()
				key = _cache_stream(args)

				if decorator.cache :
					i: int = 0
					for expires, itemkey in decorator.keys :
						if expires > now : break
						del decorator.cache[itemkey]
						i += 1

					if i == len(decorator.keys) :
						decorator.keys.clear()
					elif i :
						decorator.keys = decorator.keys[-len(decorator.cache):]

					if key in decorator.cache :
						return decorator.cache[key]

				data: Any = await func(*args, **kwargs)
				decorator.cache[key]: Any = data
				decorator.keys.append((now + TTL, key))

				return data

		else :
			@wraps(func)
			def wrapper(*args: Tuple[Any], **kwargs:Dict[str, Any]) -> Any :
				now: float = time()
				key = _cache_stream(args)

				if decorator.cache :
					i: int = 0
					for expires, itemkey in decorator.keys :
						if expires > now : break
						del decorator.cache[itemkey]
						i += 1

					if i == len(decorator.keys) :
						decorator.keys.clear()
					elif i :
						decorator.keys = decorator.keys[-len(decorator.cache):]

					if key in decorator.cache :
						return decorator.cache[key]

				data: Any = func(*args, **kwargs)
				decorator.cache[key]: Any = data
				decorator.keys.append((now + TTL, key))

				return data

		return wrapper

	decorator.cache: Dict[Tuple[Hashable], Any] = { }
	decorator.keys: List[Tuple[Union[float, Hashable]]] = [ ]
	return decorator


# PascalCase because these are technically classes
def KwargsCache(TTL_seconds:float=0, TTL_minutes:float=0, TTL_hours:float=0, TTL_days:float=0, sort_keys:bool=False) -> Callable :
	TTL: float = TTL_seconds + TTL_minutes / 60 + TTL_hours / 3600 + TTL_days / 86400
	if sort_keys :
		create_key: Callable = lambda a, k : tuple((key, k[key]) for key in sorted(k.keys())) + a
	else :
		create_key: Callable = lambda a, k : tuple(k.items()) + a
	del TTL_seconds, TTL_minutes, TTL_hours, TTL_days, sort_keys


	def decorator(func: Callable) -> Callable :

		if iscoroutinefunction(func) :
			@wraps(func)
			async def wrapper(*args: Tuple[Hashable], **kwargs:Dict[str, Hashable]) -> Any :
				cache_key: Tuple[Any] = create_key(args, kwargs)
				now: float = time()

				if decorator.cache :
					i: int = 0
					for expires, key in decorator.keys :
						if expires > now : break
						del decorator.cache[key]
						i += 1

					if i == len(decorator.keys) :
						decorator.keys.clear()
					elif i :
						decorator.keys = decorator.keys[-len(decorator.cache):]

					if cache_key in decorator.cache :
						return decorator.cache[cache_key]

				data: Any = await func(*args, **kwargs)
				decorator.cache[cache_key]: Any = data
				decorator.keys.append((now + TTL, cache_key))

				return data

		else :
			@wraps(func)
			def wrapper(*args: Tuple[Hashable], **kwargs:Dict[str, Hashable]) -> Any :
				cache_key: Tuple[Any] = create_key(args, kwargs)
				now: float = time()

				if decorator.cache :
					i: int = 0
					for expires, key in decorator.keys :
						if expires > now : break
						del decorator.cache[key]
						i += 1

					if i == len(decorator.keys) :
						decorator.keys.clear()
					elif i :
						decorator.keys = decorator.keys[-len(decorator.cache):]

					if cache_key in decorator.cache :
						return decorator.cache[cache_key]

				data: Any = func(*args, **kwargs)
				decorator.cache[cache_key]: Any = data
				decorator.keys.append((now + TTL, cache_key))

				return data

		return wrapper

	decorator.cache: Dict[Tuple[Any], Any] = { }
	decorator.keys: List[Tuple[Any]] = [ ]
	return decorator


@unique
class Aggregator(Enum) :
	Sum: str = 'sum'
	Average: str = 'avg'


class SumAggregator :
	def __init__(self) :
		self.data = defaultdict(lambda : 0)
	
	def update(self, data: Dict) :
		for k in data.keys() :
			self.data[k] += data[k]
	
	def result(self) :
		value = self.data.copy()
		self.data.clear()
		return value


class AverageAggregator :
	def __init__(self) :
		self.data = defaultdict(lambda : 0)
		self.count = 0
	
	def update(self, data: Dict) :
		self.count += 1
		for k in data.keys() :
			self.data[k] += data[k]
	
	def result(self) :
		value = {
			k: v / self.count
			for k, v in self.data.items()
		}
		self.data.clear()
		self.count = 0
		return value


_aggregators: Dict[Aggregator, Callable] = {
	Aggregator.Average: AverageAggregator,
	Aggregator.Sum: SumAggregator,
}


def Aggregate(TTL_seconds:float=0, TTL_minutes:float=0, TTL_hours:float=0, TTL_days:float=0, exclusions:Iterable[str]=['self'], aggregator:Aggregator=Aggregator.Average) -> Callable :
	"""
	aggregates numeric inputs for a given count or time span
	"""

	exclusions: Set[str] = set(exclusions)
	aggregator = _aggregators[aggregator]()
	TTL: float = TTL_seconds + TTL_minutes / 60 + TTL_hours / 3600 + TTL_days / 86400
	del TTL_seconds, TTL_minutes, TTL_hours, TTL_days

	def decorator(func: Callable) -> Callable :

		arg_spec: FullArgSpec = getfullargspec(func)

		if iscoroutinefunction(func) :
			@wraps(func)
			async def wrapper(*args: Tuple[Any], **kwargs:Dict[str, Any]) -> Any :
				kwargs.update(zip(arg_spec.args, args))
				keys: Set[str] = kwargs.keys() - exclusions
				aggregator.update({
					key: kwargs[key]
					for key in keys
				})

				now: float = time()
				if now > decorator.expire :
					decorator.expire = now + TTL
					kwargs.update(aggregator.result())
					return await func(**kwargs)

		else :
			@wraps(func)
			def wrapper(*args: Tuple[Any], **kwargs:Dict[str, Any]) -> Any :
				kwargs.update(zip(arg_spec.args, args))
				keys: Set[str] = kwargs.keys() - exclusions
				aggregator.update({
					key: kwargs[key]
					for key in keys
				})

				now: float = time()
				if now > decorator.expire :
					decorator.expire = now + TTL
					kwargs.update(aggregator.result())
					return func(**kwargs)

		return wrapper

	decorator.expire: float = time() + TTL
	return decorator

"""
from kh_common.caching import Aggregate; from random import randrange
a = [randrange(10) for i in range(10)]; b = [randrange(100) for i in range(10)]; c = [randrange(1000) for i in range(10)]
@Aggregate(10)
def t(a, b, c=5) :
	print(a, b, c)

for i in range(10) :
	t(a[i], b[i], c[i])

t(1,1,1)
"""