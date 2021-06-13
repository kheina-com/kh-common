from pika import BaseConnection, BlockingConnection, ConnectionParameters
from typing import Any, Dict, Iterator, List, Tuple, Union
from kh_common.utilities import getFullyQualifiedClassName
from kh_common.config.credentials import message_queue
from kh_common.config.repo import name, short_hash
from kh_common.logging import getLogger, Logger
from pika.channel import Channel
from traceback import format_tb
from types import TracebackType
from sys import exc_info


class Receiver :

	def __init__(self) :
		self._route: str = message_queue['routing_key']
		self._connection_info: Dict[str, Union[str, int]] = message_queue['connection_info']
		self._channel_info: Dict[str, Union[float, bool]] = message_queue['channel_info']
		self._exchange_info: Dict[str, str] = message_queue.get('exchange_info')
		self.logger: Logger = getLogger()


	def consumer(self) -> Iterator[Any] :
		yield from self._recv()


	def receiveAll(self) -> List[Any] :
		return list(self._recv())


	def receiveJson(self, forcelist:bool=False) -> Union[List[Dict[str, Any]], Iterator[Dict[str, Any]]] :
		if forcelist :
			return list(map(json.loads, self._recv()))
		else :
			return map(json.loads, self._recv())


	def _recv(self) -> Iterator[Any] :
		connection: Union[BaseConnection, None] = None
		try :
			# returns a list of all messages retrieved from the message queue
			connection = BlockingConnection(ConnectionParameters(**self._connection_info))
			channel: Channel = connection.channel()

			if self._exchange_info :
				channel.exchange_declare(**self._exchange_info)
				name: str = channel.queue_declare(self._route).method.queue
				channel.queue_bind(routing_key=self._route, queue=name, exchange=self._exchange_info['exchange'])

			else :
				channel.queue_declare(self._route)
				name: str = self._route

			it: Iterator[Tuple[Any]] = channel.consume(name, **self._channel_info)

			ack: int = -1
			for method_frame, _, body in it :
				if body :
					yield body
					ack = max(ack, method_frame.delivery_tag)
				else :
					break

			if ack >= 0 :
				channel.basic_ack(delivery_tag=ack, multiple=True)

			channel.cancel()
		
		except :
			self.logger.warning('message queue crashed unexpectedly.', exc_info=True)

		finally :
			# don't channel.cancel here since, if it fails, we want the messages to remain in the queue
			try :
				if connection :
					connection.close()

			except Exception as e :
				self.logger.warning('unexpected exception occurred during message queue close.', exc_info=e)
