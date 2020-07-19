from time import time


def SimpleCache(TTL=300) :
	def decorator(func) :
		def wrapper(*args, **kwargs) :
			now = time()
			if now > decorator.expire :
				decorator.data = func(*args, **kwargs)
				decorator.expire = now + TTL
			return decorator.data
		return wrapper
	decorator.expire = 0
	decorator.data = None
	return decorator


def ArgsCache(TTL=300, classfunc=None) :
	def decorator(func) :
		if classfunc :
			def wrapper(*args) :
				key = args[1:]

				now = time()

				for purgekey, value in decorator.cache.items() :
					if now > value['expire'] :
						del decorator.cache[purgekey]

				if key in decorator.cache :
					cache = decorator.cache[key]
					expire = cache['expire']
				else :
					cache = decorator.cache[key] = { }
					expire = 0

				if now > expire :
					cache['data'] = func(*args)
					cache['expire'] = now + TTL

				return cache['data']
		else :
			def wrapper(*args) :
				if args in decorator.cache :
					cache = decorator.cache[args]
					expire = cache['expire']
				else :
					cache = decorator.cache[key] = { }
					expire = 0

				now = time()

				if now > expire :
					cache['data'] = func(*args)
					cache['expire'] = now + TTL

				return cache['data']

		return wrapper
	decorator.cache = { }
	return decorator
