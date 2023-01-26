from tests.utilities.credentials import injectCredentials


injectCredentials(telegram={ 'telegram_access_token': 'test_token', 'telegram_bot_id': 1234567890 })

import pytest

from kh_common.telegram import Listener
from kh_common.models.telegram import Message, ChatType
from kh_common.datetime import datetime


class TestListener :

	def createTelegramMessage(self, command=None, text=None, is_chat=False) :
		message = {
			'message_id': 123,
			'date': datetime.now(),
			'from': {
				'id': 1,
				'first_name': 'test',
				'is_bot': False,
			},
			'chat': {
				'id': 1 + is_chat,
				'type': ChatType.private,
			},
		}

		entities = []

		if command :
			if text :
				text = ' '.join([command, text])

			else :
				text = command

			entities.append({
				'offset': 0,
				'length': len(command),
				'type': 'bot_command',
			})

		message['text'] = text or ''
		message['entities'] = entities

		return Message.parse_obj(message)


	@pytest.mark.asyncio
	async def test_ProcessCallsFunc_FuncCalledWithAppropriateArgs(self) :
		# arrange
		class DummyListener(Listener) :
			def __init__(self) :
				Listener.__init__(self)

			async def handleUnknownCommand(self, user, chat, message) :
				return { 'user': user, 'chat': chat, 'message': message }

		listener = DummyListener()
		message = self.createTelegramMessage(command='/test')

		# act
		result = await listener.parseMessage(message)

		# assert
		assert 1 == result['user'] == result['chat']
		assert message == result['message']


	@pytest.mark.asyncio
	async def test_CustomResponse_ResponseRunsSendMessage(self) :
		# arrange
		response = 'DUMMY RESPONSE'

		class DummyListener(Listener) :
			def __init__(self) :
				Listener.__init__(self, responses={ '/test': response })

			async def sendMessage(self, recipient, message, parse_mode='HTML') :
				return { 'recipient': recipient, 'message': message }

		listener = DummyListener()
		message = self.createTelegramMessage(command='/test')

		# act
		result = await listener.parseMessage(message)

		# assert
		assert { 'recipient': 1, 'message': response } == result


	@pytest.mark.asyncio
	async def test_CustomCommand_CommandRunsAppropriateCommand(self) :
		# arrange
		class DummyListener(Listener) :
			def __init__(self) :
				Listener.__init__(self, commands={ '/test': self.test })

			async def test(self, user, command) :
				return { 'user': user, 'command': command }

		listener = DummyListener()
		message = self.createTelegramMessage(command='/test')

		# act
		result = await listener.parseMessage(message)

		# assert
		assert { 'user': 1, 'command': '/test' } == result


	@pytest.mark.asyncio
	async def test_HandleNonCommand_NonCommandGivenNecessaryArgs(self) :
		# arrange
		class DummyListener(Listener) :
			def __init__(self) :
				Listener.__init__(self)

			async def handleNonCommand(self, user, message) :
				return { 'user': user, 'message': message }

		listener = DummyListener()
		message = self.createTelegramMessage(text='test')

		# act
		result = await listener.parseMessage(message)

		# assert
		assert { 'user': 1, 'message': message } == result


	@pytest.mark.asyncio
	async def test_DisallowedChats_BotDoesntRespond(self) :
		# arrange
		class DummyListener(Listener) :
			def __init__(self) :
				Listener.__init__(self, responses={ '/test': 'test' }, allow_chats=False)

			async def sendMessage(self, recipient, message, parse_mode='HTML') :
				return { 'recipient': recipient, 'response': message }

		listener = DummyListener()
		message = self.createTelegramMessage(command='/test@test', is_chat=True)

		# act
		result = await listener.parseMessage(message)

		# assert
		assert True == result


	@pytest.mark.asyncio
	async def test_DisallowedChats_BotRespondToDm(self) :
		# arrange
		response = 'DUMMY RESPONSE'

		class DummyListener(Listener) :
			def __init__(self) :
				Listener.__init__(self, responses={ '/test': response }, allow_chats=False)

			async def sendMessage(self, recipient, message, parse_mode='HTML') :
				return { 'recipient': recipient, 'response': message }

		listener = DummyListener()
		message = self.createTelegramMessage(command='/test')

		# act
		result = await listener.parseMessage(message)

		# assert
		assert { 'recipient': 1, 'response': response } == result


	@pytest.mark.asyncio
	async def test_AllowedChats_BotIgnoresCommandWithoutName(self) :
		# arrange
		response = 'DUMMY RESPONSE'

		class DummyListener(Listener) :
			def __init__(self) :
				Listener.__init__(self, responses={ '/test': response }, allow_chats=True, bot_name='test')

			async def sendMessage(self, recipient, message, parse_mode='HTML') :
				return { 'recipient': recipient, 'response': message }

		listener = DummyListener()
		message = self.createTelegramMessage(command='/test', is_chat=True)

		# act
		result = await listener.parseMessage(message)

		# assert
		assert True == result


	@pytest.mark.asyncio
	async def test_AllowedChats_BotIgnoresCommandWithWrongName(self) :
		# arrange
		response = 'DUMMY RESPONSE'

		class DummyListener(Listener) :
			def __init__(self) :
				Listener.__init__(self, responses={ '/test': response }, allow_chats=True, bot_name='test')

			async def sendMessage(self, recipient, message, parse_mode='HTML') :
				return { 'recipient': recipient, 'response': message }

		listener = DummyListener()
		message = self.createTelegramMessage(command='/test@someotherbot', is_chat=True)

		# act
		result = await listener.parseMessage(message)

		# assert
		assert True == result


	@pytest.mark.asyncio
	async def test_AllowedChats_BotRespondsToCommandWithName(self) :
		# arrange
		response = 'DUMMY RESPONSE'

		class DummyListener(Listener) :
			def __init__(self) :
				Listener.__init__(self, responses={ '/test': response }, allow_chats=True, bot_name='test')

			async def sendMessage(self, recipient, message, parse_mode='HTML') :
				return { 'recipient': recipient, 'response': message }

		listener = DummyListener()
		message = self.createTelegramMessage(command='/test@test', is_chat=True)

		# act
		result = await listener.parseMessage(message)

		# assert
		assert { 'recipient': message.chat.id, 'response': response } == result
