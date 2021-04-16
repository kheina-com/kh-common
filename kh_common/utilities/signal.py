from signal import signal, SIGINT, SIGTERM


class Terminated:

	alive = True
	_run_on_term = []

	def on_terminate(func, *args, **kwargs) :
		Terminated._run_on_term.append((func, args, kwargs))

	def terminate(signum, frame):
		for func, args, kwargs in Terminated._run_on_term :
			func(*args, **kwargs)

		Terminated._run_on_term.clear()
		Terminated.alive = False

	def __call__(self = None) :
		return not Terminated.alive

	signal(SIGINT, terminate)
	signal(SIGTERM, terminate)
