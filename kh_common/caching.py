from typing import Any, Callable, Dict, Hashable, Iterable, Tuple, Union
from inspect import FullArgSpec, getfullargspec, iscoroutinefunction
from collections import defaultdict, OrderedDict
from functools import wraps
from copy import deepcopy
from asyncio import Lock
from math import sqrt
from time import time


class CalcDict(dict) :

	def __init__(self, default: Callable[[Hashable], Any]) -> None :
		self.default: Callable = default


	def setdefault(self, default: Callable[[Hashable], Any]) -> None :
		self.default = default


	def __missing__(self, key: Hashable) -> Any:
		self[key] = self.default(key)
		return self[key]


_conversions: Dict[type, Callable] = {
	dict: lambda x : tuple((key, x[key]) for key in sorted(x.keys())),
	list: tuple,
}


def _convert_item(item: Any) -> Any :
	if isinstance(item, str) :
		return item
	if isinstance(item, Iterable) :
		return _cache_stream(item)
	for cls in type(item).__mro__ :
		if cls in _conversions :
			return _conversions[cls](item)
	return item


def _cache_stream(stream: Iterable) :
	if isinstance(stream, dict) :
		return tuple((key, _convert_item(stream[key])) for key in sorted(stream.keys()))

	else :
		return tuple(map(_convert_item, stream))


def SimpleCache(TTL_seconds:float=0, TTL_minutes:float=0, TTL_hours:float=0, TTL_days:float=0) -> Callable :
	"""
	stores single result for all arguments used to call.
	any arguments/keywords can be used.
	"""
	TTL: float = TTL_seconds + TTL_minutes * 60 + TTL_hours * 3600 + TTL_days * 86400
	del TTL_seconds, TTL_minutes, TTL_hours, TTL_days

	def decorator(func: Callable) -> Callable :
		if iscoroutinefunction(func) :
			@wraps(func)
			async def wrapper(*args: Tuple[Any], **kwargs:Dict[str, Any]) -> Any :
				async with decorator.lock :
					if time() > decorator.expire :
						decorator.expire = time() + TTL
						decorator.data = await func(*args, **kwargs)
				return deepcopy(decorator.data)

		else :
			@wraps(func)
			def wrapper(*args: Tuple[Any], **kwargs:Dict[str, Any]) -> Any :
				if time() > decorator.expire :
					decorator.expire = time() + TTL
					decorator.data = func(*args, **kwargs)
				return deepcopy(decorator.data)

		return wrapper
	decorator.expire = 0
	decorator.data = None
	decorator.lock = Lock()
	return decorator


def __clear_cache__(cache: OrderedDict) :
	now: float = time()

	try :
		while True :
			cache_key = next(cache.__iter__())
			if cache[cache_key]['e'] >= now : break
			del cache[cache_key]

	except StopIteration :
		pass


def ArgsCache(TTL_seconds:float=0, TTL_minutes:float=0, TTL_hours:float=0, TTL_days:float=0) -> Callable :
	"""
	stores results for every argument used to call.
	requires all arguments to be hashable, keywords are not included in the cache key.
	"""
	TTL: float = TTL_seconds + TTL_minutes * 60 + TTL_hours * 3600 + TTL_days * 86400
	del TTL_seconds, TTL_minutes, TTL_hours, TTL_days

	def decorator(func: Callable) -> Callable :

		if iscoroutinefunction(func) :
			@wraps(func)
			async def wrapper(*key: Tuple[Any], **kwargs:Dict[str, Any]) -> Any :
				async with decorator.lock :
					__clear_cache__(decorator.cache)

				if key in decorator.cache :
					return deepcopy(decorator.cache[key]['d'])

				data: Any = await func(*key, **kwargs)
				decorator.cache[key] = { 'd': data, 'e': time() + TTL }

				return deepcopy(data)

		else :
			@wraps(func)
			def wrapper(*key: Tuple[Any], **kwargs:Dict[str, Any]) -> Any :
				__clear_cache__(decorator.cache)

				if key in decorator.cache :
					return deepcopy(decorator.cache[key]['d'])

				data: Any = func(*key, **kwargs)
				decorator.cache[key] = { 'd': data, 'e': time() + TTL }

				return deepcopy(data)

		return wrapper

	decorator.cache = OrderedDict()
	decorator.lock = Lock()
	return decorator


def KwargsCache(TTL_seconds:float=0, TTL_minutes:float=0, TTL_hours:float=0, TTL_days:float=0) -> Callable :
	"""
	stores results for every argument used to call.
	recursively converts all arguments/keywords into hashable types, if possible.
	"""
	TTL: float = TTL_seconds + TTL_minutes * 60 + TTL_hours * 3600 + TTL_days * 86400
	del TTL_seconds, TTL_minutes, TTL_hours, TTL_days


	def decorator(func: Callable) -> Callable :

		if iscoroutinefunction(func) :
			@wraps(func)
			async def wrapper(*args: Tuple[Hashable], **kwargs:Dict[str, Hashable]) -> Any :
				key: Tuple[Any] = _cache_stream([args, kwargs])

				async with decorator.lock :
					__clear_cache__(decorator.cache)

				if key in decorator.cache :
					return deepcopy(decorator.cache[key]['d'])

				data: Any = await func(*args, **kwargs)
				decorator.cache[key] = { 'd': data, 'e': time() + TTL }

				return deepcopy(data)

		else :
			@wraps(func)
			def wrapper(*args: Tuple[Hashable], **kwargs:Dict[str, Hashable]) -> Any :
				key: Tuple[Any] = _cache_stream([args, kwargs])

				__clear_cache__(decorator.cache)

				if key in decorator.cache :
					return deepcopy(decorator.cache[key]['d'])

				data: Any = func(*args, **kwargs)
				decorator.cache[key] = { 'd': data, 'e': time() + TTL }

				return deepcopy(data)

		return wrapper

	decorator.cache = OrderedDict()
	decorator.lock = Lock()
	return decorator


class SumAggregator :
	def __init__(self) :
		self.data = defaultdict(lambda : 0)
	
	def update(self, data: Dict) :
		for k, v in data.items() :
			self.data[k] += v
	
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
		for k, v in data.items() :
			self.data[k] += (v - self.data[k]) / self.count
	
	def result(self) :
		value = self.data.copy()
		self.data.clear()
		self.count = 0
		return value


class StandardDeviation :
	def __init__(self, count, avg, q_value) :
		self.average: float = avg
		self.count: int = count
		self.variance: float = q_value / (count - 1)
		self.deviation: float = sqrt(self.variance)


class StandardDeviationAggregator :
	def __init__(self) :
		self.avg = defaultdict(lambda : 0)
		self.variance = defaultdict(lambda : 0)
		self.count = 0

	def update(self, data: Dict) :
		self.count += 1
		for k, v in data.items() :
			prev_avg = self.avg[k]
			self.avg[k] += (v - prev_avg) / self.count
			self.variance[k] += (v - prev_avg) * (v - self.avg[k])

	def result(self) :
		value = {
			k: StandardDeviation(self.count, avg, self.variance[k])
			for k, avg in self.avg.items()
		}
		self.count = 0
		self.avg.clear()
		self.variance.clear()
		return value


class Aggregator :
	Sum: type = SumAggregator
	Average: type = AverageAggregator
	StandardDeviation: type = StandardDeviationAggregator


def Aggregate(TTL_seconds:float=0, TTL_minutes:float=0, TTL_hours:float=0, TTL_days:float=0, exclusions:Iterable[str]=['self'], aggregator:Aggregator=Aggregator.Average) -> Callable :
	"""
	aggregates numeric inputs for a given time span
	"""

	exclusions: Set[str] = set(exclusions)
	aggregator = aggregator()
	TTL: float = TTL_seconds + TTL_minutes * 60 + TTL_hours * 3600 + TTL_days * 86400
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

	decorator.expire = time() + TTL
	return decorator
