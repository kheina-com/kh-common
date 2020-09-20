from time import time


# PascalCase because these are technically classes
def SimpleCache(TTL_seconds=0, TTL_minutes=0, TTL_hours=0, TTL_days=0) :
	TTL: float = TTL_seconds + TTL_minutes / 60 + TTL_hours / 3600 + TTL_days / 86400
	del TTL_seconds, TTL_minutes, TTL_hours, TTL_days

	def decorator(func) :
		def wrapper(*args, **kwargs) :
			now = time()
			if now > decorator.expire :
				decorator.expire = now + TTL
				decorator.data = func(*args, **kwargs)
			return decorator.data
		return wrapper
	decorator.expire = 0
	decorator.data = None
	return decorator


# PascalCase because these are technically classes
def ArgsCache(TTL_seconds=0, TTL_minutes=0, TTL_hours=0, TTL_days=0) :
	TTL: float = TTL_seconds + TTL_minutes / 60 + TTL_hours / 3600 + TTL_days / 86400
	del TTL_seconds, TTL_minutes, TTL_hours, TTL_days

	def decorator(func) :
		def wrapper(*args) :
			now = time()

			if decorator.cache :
				i = 0
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
			data = decorator.cache[args] = func(*args)

			return data

		return wrapper

	decorator.cache = { }
	decorator.keys = [ ]
	return decorator


# PascalCase because these are technically classes
def KwargsCache(TTL_seconds=0, TTL_minutes=0, TTL_hours=0, TTL_days=0, sort_keys=False) :
	TTL: float = TTL_seconds + TTL_minutes / 60 + TTL_hours / 3600 + TTL_days / 86400
	if sort_keys :
		create_key = lambda a, k : tuple((key, k[key]) for key in sorted(k.keys())) + a
	else :
		create_key = lambda a, k : tuple(k.items()) + a
	del TTL_seconds, TTL_minutes, TTL_hours, TTL_days, sort_keys


	def decorator(func) :
		def wrapper(*args, **kwargs) :
			cache_key = create_key(args, kwargs)
			now = time()

			if decorator.cache :
				i = 0
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
			data = decorator.cache[cache_key] = func(*args, **kwargs)

			return data

		return wrapper

	decorator.cache = { }
	decorator.keys = [ ]
	return decorator
