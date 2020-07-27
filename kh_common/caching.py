from sched import scheduler
from time import time


# PascalCase because these are technically classes
def SimpleCache(TTL=300) :
	def decorator(func) :
		def wrapper(*args, **kwargs) :
			now = time()
			if now > decorator.expire :
				# set expire first so that another thread doesn't enter this block
				decorator.expire = now + TTL
				decorator.data = func(*args, **kwargs)
			return decorator.data
		return wrapper
	decorator.expire = 0
	decorator.data = None
	return decorator


# PascalCase because these are technically classes
def ArgsCache(TTL=300) :
	class CachedObject :
		def __init__(self, data=None) :
			self.data = data
			self.expires = time() + TTL

	def decorator(func) :

		def wrapper(*args) :

			now = time()
			if args in decorator.cache and decorator.cache[args].expires > now :
				return decorator.cache[args].data

			decorator.cache[args] = CachedObject(func(*args))

			return decorator.cache[args].data

		return wrapper

	decorator.cache = { }
	return decorator
