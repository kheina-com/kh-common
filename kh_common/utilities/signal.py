from signal import signal, SIGINT, SIGTERM


class Terminated:

	alive = True

	def terminate(signum, frame):
		Terminated.alive = False

	def __call__(self = None) :
		return not Terminated.alive

	signal(SIGINT, terminate)
	signal(SIGTERM, terminate)
