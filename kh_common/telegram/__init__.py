from kh_common.config.credentials import telegram
from asyncio import ensure_future, Queue, sleep
from kh_common.caching import Aggregate
from kh_common import logging
import requests
import json


logger = logging.getLogger()


class QuitParsing(Exception) :
	pass


class Listener :

	def __init__(self,
		looptime: float = 1,
		threads: int = 1,
		allow_chats: bool = False,
		timeout: float = 30,
		# commands that don't need to run any logic
		responses: dict = { },
		# commands that actually require logic to be performed
		commands: dict = { },
	) :
		self.looptime = looptime
		self.allow_chats = allow_chats
		self.timeout = timeout

		self._telegram_access_token = telegram['telegram_access_token']
		self._telegram_bot_id = telegram['telegram_bot_id']

		self.commands = commands
		self.responses = responses

		self.queue = Queue()


	# parse_mode = MarkdownV2 or HTML
	async def sendMessage(self, user, message, parse_mode='HTML') :
		request = f'https://api.telegram.org/bot{self._telegram_access_token}/sendMessage'
		errorMessage = 'failed to send notification to telegram.'
		info = None
		for _ in range(5) :
			try :
				async with async_request(
					'POST',
					request,
					json={
						'parse_mode': parse_mode,
						'chat_id': recipient,
						'text': message,
					},
					timeout=ClientTimeout(Notifier.Timeout),
				) as response :
					info = await response.json()
					if not info['ok'] :
						break
					return True
			except :
				pass

		logger.error({
			'info': info,
			'message': errorMessage,
			'request': request,
			'telegram message': message,
		})
		return False


	async def handleNonCommand(self, user, chat, message) :
		await self.sendMessage(user, 'sorry, I only understand bot commands right now.')


	async def handleParseError(self, user, *args, **kwargs) :
		await self.sendMessage(user, "sorry, I didn't understand that command. to see a list of my commands, try /help")


	async def parseMessage(self, message) :
		user = message['from']['id']
		chat = message['chat']['id']
		if user != chat and not self.allow_chats :
			return True

		if not 'entities' in message :
			return await self.sendMessage(user, 'sorry, I only understand bot commands right now.')

		entity = next(filter(lambda x : x['type'] == 'bot_command', message['entities']))
		if not entity :
			return await self.handleNonCommand(self, user, chat, message)

		end = entity['offset'] + entity['length']
		command = message['text'][entity['offset']:end]

		if command in self.responses :
			return await self.sendMessage(user, self.responses[command])

		text = message['text'][end:].strip()

		if command in self.commands :
			return await self.commands[command](user, chat, text, message)

		return await self.handleParseError(user, chat, command, text, message)


	async def processQueue(self) :
		while True :
			update = await self.queue.get()

			try :
				self.parseMessage(update['message'])

			except QuitParsing :
				pass

			except :
				logger.exception({
					'message': 'failed to parse message.',
					'update': update,
				})

			self.queue.task_done()


	async def run(self, threads:int=1) :
		threads = [ensure_future(self.processQueue()) for _ in range(threads)]
		await self.recv()


	async def recv(self) :
		# just let it fail if it's not json serialized
		request = f'https://api.telegram.org/bot{self._telegram_access_token}/getUpdates?offset='
		mostrecent = 0
		while True :
			try :
				async with async_request(
					'GET',
					request + str(mostrecent),
					timeout=ClientTimeout(self.timeout),
				) as response :
					updates = await response.json()

					if updates['ok'] and updates['result'] :
						mostrecent = updates['result'][-1]['update_id'] + 1
						for update in updates['result'] :
							await self.queue.put(update)

					else :
						logger.error({
							'message': 'failed to read updates from telegram.',
							'updates': updates,
						})
						sleep(self.looptime)

				self._logQueueSize(self.queue.qsize())

			except :
				logger.exception('failed to read updates from telegram.')


	@Aggregate(60)
	def _logQueueSize(self, queue_size: int) :
		logger.info({
			'queue_size': queue_size,
		})