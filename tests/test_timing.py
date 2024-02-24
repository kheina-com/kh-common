import asyncio
import logging
import time
from ast import literal_eval

import pytest

from kh_common.timing import timed
from tests.utilities.logging import Handler


logging.root.setLevel(logging.INFO)


class TestTimedDecorator :

	def test_Timed_NoChildrenNoParams_FuncIsTimedAndCorrect(self) :

		# arrange
		Handler.messages.clear()

		@timed
		def test() :
			time.sleep(0.01)

		# act
		test()

		# assert
		assert 1 == len(Handler.messages)
		assert Handler.messages[0].levelname == 'INFO'

		# python's logger turns all logs into strings, turn it back into a dict
		message = literal_eval(Handler.messages[0].message)
		assert 'test' == message['name']
		assert 0.010 <= message['total'] <= 0.011
		assert 0 == len(message['nested'])


	def test_Timed_ManyChildrenNoParams_AllChildrenTimed(self) :

		# arrange
		Handler.messages.clear()

		@timed
		def child_func() :
			time.sleep(0.01)

		@timed
		def test() :
			child_func()
			child_func()
			child_func()

		# act
		test()

		# assert
		assert 1 == len(Handler.messages)
		assert Handler.messages[0].levelname == 'INFO'

		# python's logger turns all logs into strings, turn it back into a dict
		message = literal_eval(Handler.messages[0].message)
		assert 'test' == message['name']
		assert 0.030 <= message['total'] <= 0.033
		assert 3 == len(message['nested'])
		for n in message['nested'] :
			assert 0.010 <= n['child_func'] <= 0.011


	def test_Timed_AsyncChildrenNoParams_AsyncChildrenNamedAndTimed(self) :

		# arrange
		Handler.messages.clear()

		@timed
		async def child_func() :
			await asyncio.sleep(0.01)

		@timed
		def test() :
			asyncio.run(child_func())
			asyncio.new_event_loop().run_until_complete(child_func())

		# act
		test()

		# assert
		assert 1 == len(Handler.messages)
		assert Handler.messages[0].levelname == 'INFO'

		# python's logger turns all logs into strings, turn it back into a dict
		message = literal_eval(Handler.messages[0].message)
		assert 'test' == message['name']
		assert 0.020 <= message['total'] <= 0.022
		assert 2 == len(message['nested'])
		for n in message['nested'] :
			assert 0.010 <= n['async.child_func'] <= 0.011


	def test_Timed_ManyhildrenChildParam_ChildSkipsLogAlone(self) :

		# arrange
		Handler.messages.clear()

		@timed(child=True)
		def child_func() :
			time.sleep(0.01)

		@timed(op='file.test.func')
		def test() :
			child_func()

		# act
		test()
		child_func()

		# assert
		assert 1 == len(Handler.messages)
		assert Handler.messages[0].levelname == 'INFO'

		# python's logger turns all logs into strings, turn it back into a dict
		message = literal_eval(Handler.messages[0].message)
		assert 'file.test.func' == message['name']
		assert 0.010 <= message['total'] <= 0.011
		assert 1 == len(message['nested'])
		for n in message['nested'] :
			assert 0.010 <= n['child_func'] <= 0.011


@pytest.mark.asyncio
class TestTimedDecoratorAsync :

	async def test_TimedAsync_NoChildrenNoParams_FuncIsTimedAndCorrect(self) :

		# arrange
		Handler.messages.clear()

		@timed
		async def test() :
			await asyncio.sleep(0.01)

		# act
		await test()

		# assert
		assert 1 == len(Handler.messages)
		assert Handler.messages[0].levelname == 'INFO'

		# python's logger turns all logs into strings, turn it back into a dict
		message = literal_eval(Handler.messages[0].message)
		assert 'test' == message['name']
		assert 0.010 <= message['async.total'] <= 0.011
		assert 0 == len(message['nested'])


	async def test_TimedAsync_ManyChildrenNoParams_AllChildrenTimed(self) :

		# arrange
		Handler.messages.clear()

		@timed
		def child_func() :
			time.sleep(0.01)

		@timed
		async def test() :
			child_func()
			child_func()
			child_func()

		# act
		await test()

		# assert
		assert 1 == len(Handler.messages)
		assert Handler.messages[0].levelname == 'INFO'

		# python's logger turns all logs into strings, turn it back into a dict
		message = literal_eval(Handler.messages[0].message)
		assert 'test' == message['name']
		assert 0.030 <= message['async.total'] <= 0.033
		assert 3 == len(message['nested'])
		for n in message['nested'] :
			assert 0.010 <= n['child_func'] <= 0.011


	async def test_TimedAsync_AsyncChildrenNoParams_AsyncChildrenNamedAndTimed(self) :

		# arrange
		Handler.messages.clear()

		@timed
		async def child_func() :
			await asyncio.sleep(0.01)

		@timed
		async def test() :
			future = asyncio.ensure_future(child_func())
			task = asyncio.create_task(child_func())
			await child_func()
			await future
			await task

		# act
		await test()

		# assert
		assert 1 == len(Handler.messages)
		assert Handler.messages[0].levelname == 'INFO'

		# python's logger turns all logs into strings, turn it back into a dict
		message = literal_eval(Handler.messages[0].message)
		assert 'test' == message['name']
		assert 0.030 <= message['total'] <= 0.033
		assert 3 == len(message['nested'])
		for n in message['nested'] :
			assert 0.010 <= n['async.child_func'] <= 0.011
