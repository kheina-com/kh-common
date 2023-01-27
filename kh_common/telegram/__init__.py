from asyncio import Queue, QueueEmpty, ensure_future, sleep
from asyncio import wait as WaitAll
from collections import defaultdict
from inspect import getfullargspec
from typing import List, Optional, Union

from aiohttp import ClientTimeout
from aiohttp import request as async_request

from kh_common.caching import Aggregate
from kh_common.config.credentials import telegram
from kh_common.logging import getLogger
from kh_common.models.telegram import Message, MessageEntity, MessageEntityType, Update, Updates, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply
from kh_common.utilities.signal import Terminated


logger = getLogger()


class QuitParsing(Exception) :
	pass


class Listener :

	def __init__(self,
		loop_time: float = 1,
		queue_empty_wait: float = 1,
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
		"""
		:param loop_time: how long to wait between calls to getUpdates
		:param queue_empty_wait: how long to wait for more messages to be added to the queue when empty
		:param threads: how many message processing threads to spin up
		:param allow_chats: whether or not the bot should react to commands sent in chats. NOTE: chat commands need the bot's username sent in the command. EX: /help@botname
		:param bot_name: the bot's username (used by allow_chats)
		:param timeout: timeout used when sending requests to telegram's bot api
		:param text_limit: used to split long messages into multiple individual messages
		:param text_breaks: used to determine a good spot to break a message. NOTE: earlier splits have higher priority (used by text_limit)
		:param responses: used to register commands that have a static string response, like /help or /commands. format: responses={ "/command": "string response" }
		:param commands: used to register commands that require logic to form a response. functions are async and can have any or none of the following params: user, chat, is_chat, message, text, command. format: commands={ "/command": self.my_command_handler }
			user: contains the user id of the sent message
			chat: contains the chat id the message was sent in
			is_chat: boolean determining if the chat was a group or supergroup or other non-direct message
			message: contains the full message object
			text: the text of the message, with the command itself removed. EX: "/help me" becomes "me"
			command: contains the text of the command received. should match the key of this dictionary (will not contain bot name)
		"""
		self.loop_time = loop_time
		self.queue_empty_wait = queue_empty_wait
		self.allow_chats = allow_chats
		self.timeout = timeout
		self.threads = threads
		self.bot_name = bot_name.lower() if bot_name else None

		self._telegram_access_token = telegram['telegram_access_token']
		self._telegram_bot_id = telegram['telegram_bot_id']

		self.commands = defaultdict(lambda : self.handleUnknownCommand, commands)
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
	async def sendMessage(self, recipient, message, parse_mode: str = 'HTML', reply_to: int = None, markup: Optional[Union[InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply]] = None) :
		messages = self.splitMessage(message)
		reply_markup: dict = None
		success = False

		for i, m in enumerate(messages) :
			if i == len(messages) - 1 :
				if markup :
					# passthrough encoder so that it's still a dict, and not a string
					reply_markup = markup.json(encoder=lambda x : x, exclude_unset=True)

				success = await self._sendSingleMessage(recipient, m, parse_mode, reply_to, reply_markup, i, len(messages))

			else :
				success = await self._sendSingleMessage(recipient, m, parse_mode, reply_to, None, i, len(messages))

			if not success :
				return False

		return success


	async def _sendSingleMessage(self, recipient, message, parse_mode: str = 'HTML', reply_to: int = None, reply_markup: Optional[dict] = None, message_index: int = 0, message_count: int = 1) :
		request = f'https://api.telegram.org/bot{self._telegram_access_token}/sendMessage'
		error = 'failed to send notification to telegram.'
		info = None
		body = {
			'parse_mode': parse_mode,
			'chat_id': recipient,
			'text': message,
		}

		if reply_to :
			body['reply_to_message_id'] = reply_to

		if reply_markup :
			body['reply_markup'] = reply_markup

		for _ in range(5) :
			try :
				async with async_request(
					'POST',
					request,
					json=body,
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
					'index': message_index,
					'total': message_count,
					**body,
				},
			},
		})
		return False


	async def handleNonCommand(self, chat, is_chat, **kwargs) :
		if not is_chat :
			ensure_future(self._sendSingleMessage(chat, 'Sorry, I only understand bot commands right now.'))


	async def handleUnknownCommand(self, chat, **kwargs) :
		ensure_future(self._sendSingleMessage(chat, "Sorry, I didn't understand that command. to see a list of my commands, try /help"))


	async def parseUpdateWithoutMessage(self, update: Update) -> None :
		logger.warning("Received an update from telegram without a message. Processing updates without messages isn't supported yet. You can add support yourself, by overwriting the parseUpdateWithoutMessage function.")


	async def parseMessage(self, message: Message) -> None :
		user = message.from_user.id
		chat = message.chat.id
		is_chat = False

		if user != chat :
			if not self.allow_chats :
				return True

			is_chat = True

		args = {
			'user': user,
			'chat': chat,
			'is_chat': is_chat,
			'message': message,
		}

		try :
			entity: MessageEntity = next(filter(lambda x : x.type == MessageEntityType.bot_command, message.entities))

		except StopIteration :
			arg_spec = getfullargspec(self.handleNonCommand)

			if arg_spec.varkw :
				return await self.handleNonCommand(**args)

			return await self.handleNonCommand(**{ k: args[k] for k in arg_spec.args[1:] + arg_spec.kwonlyargs })

		end: int = entity.offset + entity.length
		command: str = message.text[entity.offset:end]

		if is_chat :
			command_split = command.split('@')
			if len(command_split) <= 1 :
				return True

			if command_split[1].lower() != self.bot_name :
				return True

			command = command_split[0]

		if command in self.responses :
			return await self.sendMessage(chat, self.responses[command])

		args.update({
			'text': message.text[end:].strip(),
			'command': command,
		})

		func = self.commands[command]
		arg_spec = getfullargspec(func)

		if arg_spec.varkw :
			return await func(**args)

		return await func(**{ k: args[k] for k in arg_spec.args[1:] + arg_spec.kwonlyargs })


	async def processQueue(self) :
		while Terminated.alive or not self.queue.empty() :
			try :
				update: Update = self.queue.get_nowait()

			except QueueEmpty :
				await sleep(self.queue_empty_wait)
				continue

			try :
				if update.message :
					await self.parseMessage(update.message)

				else :
					await self.parseUpdateWithoutMessage(update)

			except QuitParsing :
				pass

			except :
				logger.exception({
					'message': 'failed to parse message.',
					'update': update,
				})

			self.queue.task_done()


	async def run(self) :
		threads = [self.processQueue() for _ in range(self.threads)] + [self.recv()]
		await WaitAll(threads)


	async def recv(self) :
		# just let it fail if it's not json serialized
		request = f'https://api.telegram.org/bot{self._telegram_access_token}/getUpdates?offset='
		mostrecent = 0
		while Terminated.alive :
			try :
				async with async_request(
					'GET',
					request + str(mostrecent),
					timeout=ClientTimeout(self.timeout),
				) as response :
					updates: Updates = Updates.parse_raw(await response.read())

					if not updates.ok :
						logger.error({
							'message': 'failed to read updates from telegram.',
							'updates': updates,
						})
						await sleep(self.loop_time)

					elif updates.result :
						mostrecent = updates.result[-1].update_id + 1
						for update in updates.result :
							await self.queue.put(update)

					else :
						await sleep(self.loop_time)

				self._logQueueSize(self.queue.qsize())

			except :
				logger.exception('failed to read updates from telegram.')


	@Aggregate(60)
	def _logQueueSize(self, queue_size: int) :
		logger.info({
			'queue_size': queue_size,
		})
