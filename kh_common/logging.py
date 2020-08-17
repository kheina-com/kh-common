from kh_common import getFullyQualifiedClassName
from traceback import format_tb
import logging


class TerminalAgent :

	loggable = (str, int, float, type(None))

	def __init__(self) :
		import time
		import json
		self.time = time
		self.json = json

	def flatten(self, it) :
		if isinstance(it, (tuple, list, set)) :
			for i in it :
				yield from self.flatten(i)
		elif isinstance(it, dict) :
			for k, v in it.items() :
				yield from self.flatten(v)
		else :
			yield it

	def log_text(self, log, severity='INFO') :
		print('[' + self.time.asctime(self.time.localtime(self.time.time())) + ']', severity, '>', log)

	def log_struct(self, log, severity='INFO') :
		for i in self.flatten(log) :
			if not isinstance(i, TerminalAgent.loggable) :
				print('WARNING:', i, 'may not be able to be logged.')
		print('[' + self.time.asctime(self.time.localtime(self.time.time())) + ']', severity, '>', self.json.dumps(log, indent=4))


class LogHandler(logging.Handler) :

	def __init__(self, name, *args, structs=(dict, list, tuple), **kwargs) :
		logging.Handler.__init__(self, *args, **kwargs)
		self._structs = structs
		try :
			from google.cloud import logging as google_logging
			from google.auth import compute_engine
			credentials = compute_engine.Credentials()
			logging_client = google_logging.Client(credentials=credentials)
			self.agent = logging_client.logger(name)
		except :
			self.agent = TerminalAgent()


	def emit(self, record) :
		if record.args and isinstance(record.msg, str) and len(record.args) == record.msg.count('%') :
			record.msg = record.msg % record.args
		if record.exc_info :
			e = record.exc_info[1]
			errorinfo = {
				'error': f'{getFullyQualifiedClassName(e)}: {e}',
				'stacktrace': format_tb(record.exc_info[2]),
				**getattr(e, 'logdata', { }),
			}
			if isinstance(record.msg, dict) :
				errorinfo.update(record.msg)
			else :
				errorinfo.update({ 'message': record.msg })
			self.agent.log_struct(errorinfo, severity=record.levelname)
		else :
			if isinstance(record.msg, self._structs) :
				self.agent.log_struct(record.msg, severity=record.levelname)
			else :
				self.agent.log_text(str(record.msg), severity=record.levelname)


def getLogger(name, *args, level=logging.INFO, filter=lambda x : x, disable=[], **kwargs) :
	for loggerName in disable :
		logging.getLogger(loggerName).propagate = False
	logging.root.setLevel(logging.NOTSET)
	handler = LogHandler(name, level=level)
	handler.addFilter(filter)
	logging.root.handlers.clear()
	logging.root.addHandler(handler)
	return logging.getLogger(name)
