from kh_common import getFullyQualifiedClassName
from traceback import format_tb
from kh_common import logging
import pika
import sys


class Receiver :

	def __init__(self, route, connection_info, channel_info, exchange_info=None) :
		self._route = route
		self._connection_info = connection_info
		self._channel_info = channel_info
		self._exchange_info = exchange_info
		self.logger = logging.getLogger(__name__)


	def consumer(self) :
		yield from self._recv()


	def receiveAll(self) :
		return list(self._recv())


	def _recv(self) :
		try :
			# returns a list of all messages retrieved from the message queue
			connection = pika.BlockingConnection(pika.ConnectionParameters(**self._connection_info))
			channel = connection.channel()

			if self._exchange_info :
				channel.exchange_declare(**self._exchange_info)
				name = channel.queue_declare(self._route).method.queue
				channel.queue_bind(routing_key=self._route, queue=name, exchange=self._exchange_info['exchange'])

			else :
				channel.queue_declare(self._route)
				name = self._route

			it = channel.consume(name, **self._channel_info)

			ack = -1
			for method_frame, _, body in it :
				if body :
					yield body
					ack = max(ack, method_frame.delivery_tag)
				else :
					break

			if ack >= 0 :
				channel.basic_ack(delivery_tag=ack, multiple=True)

			channel.cancel()
		finally :
			# don't channel.cancel here since, if it fails, we want the messages to remain in the queue
			try :
				connection.close()

			except :
				exc_type, exc_obj, exc_tb = sys.exc_info()
				self.logger.warning({
					'message': f'{GetFullyQualifiedClassName(exc_obj)}: {exc_obj}',
					'stacktrace': format_tb(exc_tb),
				})
