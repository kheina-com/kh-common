from typing import Any, Callable, Dict, Iterator, List, Tuple
from kh_common import getFullyQualifiedClassName
from traceback import format_tb
from types import ModuleType
import logging


class TerminalAgent :

	loggable: List[type] = (str, int, float, type(None))

	def __init__(self) -> type(None) :
		import time
		import json
		self.time: ModuleType = time
		self.json: ModuleType = json

	def flatten(self, it: Iterator[Any]) -> Iterator[Any] :
		if isinstance(it, (tuple, list, set)) :
			for i in it :
				yield from self.flatten(i)
		elif isinstance(it, dict) :
			for k, v in it.items() :
				yield from self.flatten(v)
		else :
			yield it

	def log_text(self, log: str, severity:str='INFO') -> type(None) :
		print('[' + self.time.asctime(self.time.localtime(self.time.time())) + ']', severity, '>', log)

	def log_struct(self, log: Dict[str, Any], severity:str='INFO') -> type(None) :
		for i in self.flatten(log) :
			if not isinstance(i, TerminalAgent.loggable) :
				print('WARNING:', i, 'may not be able to be logged.')
		print('[' + self.time.asctime(self.time.localtime(self.time.time())) + ']', severity, '>', self.json.dumps(log, indent=4))


class LogHandler(logging.Handler) :

	def __init__(self, name: str, *args: Tuple[Any], structs:Tuple[type]=(dict, list, tuple), **kwargs:[str, Any]) -> type(None) :
		logging.Handler.__init__(self, *args, **kwargs)
		self._structs: Tuple[type] = structs
		try :
			from google.cloud import logging as google_logging
			from google.auth import compute_engine
			credentials: compute_engine.credentials.Credentials = compute_engine.Credentials()
			logging_client: google_logging.client.Client = google_logging.Client(credentials=credentials)
			self.agent: google_logging.logger.Logger = logging_client.logger(name)
		except :
			self.agent: TerminalAgent = TerminalAgent()


	def emit(self, record: logging.LogRecord) -> type(None) :
		if record.args and isinstance(record.msg, str) and len(record.args) == record.msg.count('%') :
			record.msg: str = record.msg % record.args
		if record.exc_info :
			e: Exception = record.exc_info[1]
			errorinfo: Dict[str, Any] = {
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
				self.agent.log_text(str(type(record)), severity=record.levelname)


Logger: type = logging.Logger


def getLogger(name: str, *args: Tuple[Any], level:int=logging.INFO, filter:Callable=lambda x : x, disable:List[str]=[], **kwargs:[str, Any]) -> Logger :
	for loggerName in disable :
		logging.getLogger(loggerName).propagate = False
	logging.root.setLevel(logging.NOTSET)
	handler: LogHandler = LogHandler(name, level=level)
	handler.addFilter(filter)
	logging.root.handlers.clear()
	logging.root.addHandler(handler)
	return logging.getLogger(name)
