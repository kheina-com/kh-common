import time

def pretty_time(time) :
	test_time = abs(time)
	if test_time > 5400:  # 90 minutes in seconds
		return str(round(time / 3600, 2)) + 'hr'
	elif test_time > 90:
		return str(round(time / 60, 2)) + 'min'
	elif test_time < 0.000001:
		return str(round(time * 1000000000, 2)) + 'ns'
	elif test_time < 0.001:
		return str(round(time * 1000000, 2)) + 'μs'
	elif test_time < 1:
		return str(round(time * 1000, 2)) + 'ms'
	return str(round(time, 2)) + 's'

def test(*args, iterations=1000000, base=None, **kwargs) :
	start = 0
	end = 0
	functions = { a.__name__: a for a in args }
	functions.update(kwargs)

	bad = False
	match = True
	outputs = []
	for label, function in functions.items() :
		try :
			outputs.append(function())
			print(f'[{label}][output] {outputs[-1]}')
			if len(outputs) >= 2 and outputs[-1] != outputs[-2] :
				match = False
		except Exception as e :
			print(f'[{label}][error] threw {e.__class__.__name__}: {e}')
			bad = True

	if bad : return
	elif not match : print('[warning] not all outputs match. (test may not be accurate)')

	del bad
	del match
	del outputs

	if base:
		start = time.process_time()
		for i in range(iterations) :
			base()
		end = time.process_time()
	else:
		start = time.process_time()
		for i in range(iterations) :
			try : pass
			except : pass
		end = time.process_time()
	base = end - start
	print(f'[base] {pretty_time(base)} for {iterations:,} iterations ({pretty_time(base / iterations)} per iteration)')

	for label, function in functions.items() :
		start = time.process_time()
		for i in range(iterations) :
			try : function()
			except : pass
		end = time.process_time()
		function_total = (end - start) - base
		print(f'[{label}] {pretty_time(function_total)} for {iterations:,} iterations ({pretty_time(function_total / iterations)} per iteration)')
