from time import time


# PascalCase because these are technically classes
def SimpleCache(TTL=300) :
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
def ArgsCache(TTL=300) :

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
