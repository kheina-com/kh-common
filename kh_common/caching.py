from typing import Any, Callable, Dict, Hashable, Tuple, Union
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


# PascalCase because these are technically classes
def SimpleCache(TTL_seconds:float=0, TTL_minutes:float=0, TTL_hours:float=0, TTL_days:float=0) -> Callable :
	TTL: float = TTL_seconds + TTL_minutes / 60 + TTL_hours / 3600 + TTL_days / 86400
	del TTL_seconds, TTL_minutes, TTL_hours, TTL_days

	def decorator(func: Callable) -> Callable :
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
		@wraps(func)
		def wrapper(*args: Tuple[Hashable], **kwargs:Dict[str, Any]) -> Any :
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

				if args in decorator.cache :
					return decorator.cache[args]

			decorator.keys.append((now + TTL, args))
			data: Any = func(*args, **kwargs)
			decorator.cache[args]: Any = data

			return data

		return wrapper

	decorator.cache: Dict[Tuple[Any], Any] = { }
	decorator.keys: List[Tuple[Any]] = [ ]
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

			decorator.keys.append((now + TTL, cache_key))
			data: Any = func(*args, **kwargs)
			decorator.cache[cache_key]: Any = data

			return data

		return wrapper

	decorator.cache: Dict[Tuple[Any], Any] = { }
	decorator.keys: List[Tuple[Any]] = [ ]
	return decorator
