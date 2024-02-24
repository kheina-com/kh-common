import logging
from typing import List


# decorator should not change the output or fingerprint of anything, all output is done through logging, so create a new logging handler
class TestLogHandler(logging.Handler) :

	def __init__(self, *args, **kwargs) :
		super().__init__(*args, **kwargs)
		self.messages: List[logging.LogRecord] = []

	def emit(self, record: logging.LogRecord) -> None :
		self.messages.append(record)


logging.root.setLevel(logging.NOTSET)
Handler: TestLogHandler = TestLogHandler()
logging.root.handlers.clear()
logging.root.addHandler(Handler)
