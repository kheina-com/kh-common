from aiohttp import ClientTimeout, request as async_request
from kh_common.config.credentials import telegram
from asyncio import ensure_future, Queue, sleep
from kh_common.caching import Aggregate
from kh_common.logging import getLogger
from typing import List


logger = getLogger()


class QuitParsing(Exception) :
	pass


class Listener :

	def __init__(self,
		looptime: float = 1,
		threads: int = 1,
		allow_chats: bool = False,
		bot_name: str = None,
		timeout: float = 30,
		text_limit: int = 4096,
		text_breaks: List[str] = ['\n', '\t', ' '],
		# commands that don't need to run any logic
		responses: dict = { },
		# commands that actually require logic to be performed
		commands: dict = { },
	) :
		self.looptime = looptime
		self.allow_chats = allow_chats
		self.timeout = timeout
		self.threads = threads
		self.bot_name = bot_name.lower() if bot_name else None

		self._telegram_access_token = telegram['telegram_access_token']
		self._telegram_bot_id = telegram['telegram_bot_id']

		self.commands = commands
		self.responses = responses
		self.text_limit = text_limit
		self.text_breaks = text_breaks

		self.queue = Queue()


	def splitMessage(self, text: str) :
		if len(text) <= self.text_limit :
			return [text]

		messages = []

		while len(text) > self.text_limit :
			t = text[:self.text_limit]
			t_split = -1

			for splitter in self.text_breaks :
				t_split = t.rfind(splitter)

				if t_split > 0 :
					break
			
			if t_split <= 0 :
				t_split = self.text_limit
				splitter = ''

			messages.append(text[:t_split])
			text = text[t_split + len(splitter):]

		messages.append(text)
		return messages


	# parse_mode = MarkdownV2 or HTML
	async def sendMessage(self, recipient, message, parse_mode='HTML') :
		messages = self.splitMessage(message)
		success = False

		for i, m in enumerate(messages) :
			success = await self._sendSingleMessage(recipient, m, parse_mode, i, len(messages))
			if not success :
				return False

		return success


	async def _sendSingleMessage(self, recipient, message, parse_mode='HTML', message_index=0, message_count=1) :
		request = f'https://api.telegram.org/bot{self._telegram_access_token}/sendMessage'
		error = 'failed to send notification to telegram.'
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
					timeout=ClientTimeout(self.timeout),
				) as response :
					info = await response.json()
					if not info['ok'] :
						break
					return True
			except :
				pass

		logger.error({
			'info': info,
			'message': error,
			'request': {
				'url': request,
				'message': {
					'text': message,
					'index': message_index,
					'total': message_count,
				},
			},
		})
		return False


	async def handleNonCommand(self, user, chat, is_chat, message) :
		if not is_chat :
			ensure_future(self._sendSingleMessage(chat, 'Sorry, I only understand bot commands right now.'))


	async def handleParseError(self, user, chat, command, text, message) :
		ensure_future(self._sendSingleMessage(chat, "Sorry, I didn't understand that command. to see a list of my commands, try /help"))


	async def parseMessage(self, message) :
		user = message['from']['id']
		chat = message['chat']['id']
		is_chat = False

		if user != chat :
			if not self.allow_chats :
				return True

			is_chat = True

		try :
			entity = next(filter(lambda x : x['type'] == 'bot_command', message.get('entities', [])))

		except StopIteration :
			return await self.handleNonCommand(user, chat, is_chat, message)

		end = entity['offset'] + entity['length']
		command = message['text'][entity['offset']:end]

		if is_chat :
			command_split = command.split('@')
			if len(command_split) <= 1 :
				return True

			if command_split[1].lower() != self.bot_name :
				return True

			command = command_split[0]

		if command in self.responses :
			return await self.sendMessage(chat, self.responses[command])

		text = message['text'][end:].strip()

		if command in self.commands :
			return await self.commands[command](user, chat, text, message)

		return await self.handleParseError(user, chat, command, text, message)


	async def processQueue(self) :
		while True :
			update = await self.queue.get()

			try :
				await self.parseMessage(update['message'])

			except QuitParsing :
				pass

			except :
				logger.exception({
					'message': 'failed to parse message.',
					'update': update,
				})

			self.queue.task_done()


	async def run(self) :
		threads = [ensure_future(self.processQueue()) for _ in range(self.threads)]
		await self.recv()  # TODO: catch here for kill/end commands, then allow threads to clean up
		await asyncio.wait(threads)


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

					if not updates['ok'] :
						logger.error({
							'message': 'failed to read updates from telegram.',
							'updates': updates,
						})
						await sleep(self.looptime)

					elif updates['result'] :
						mostrecent = updates['result'][-1]['update_id'] + 1
						for update in updates['result'] :
							await self.queue.put(update)

					else :
						await sleep(self.looptime)

				self._logQueueSize(self.queue.qsize())

			except :
				logger.exception('failed to read updates from telegram.')


	@Aggregate(60)
	def _logQueueSize(self, queue_size: int) :
		logger.info({
			'queue_size': queue_size,
		})
