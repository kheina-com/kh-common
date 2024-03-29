from datetime import datetime, timezone
from enum import Enum
from os import getpid, kill
from signal import SIGTERM
from uuid import uuid4

from kh_common.auth import AuthToken, KhUser, Scope
from kh_common.utilities import int_from_bytes, int_to_bytes
from kh_common.utilities.json import json_stream
from kh_common.utilities.signal import Terminated


class AnEnum(Enum) :
	value_a: int = 1
	value_b: int = 2
	value_c: int = 3


class TestInit :

	def int_generator(self) :
		for i in range(100) :
			yield int('1' + '0' * i)


	def test_IntBytesConverters(self) :
		for i in self.int_generator() :
			encoded = int_to_bytes(i)
			decoded = int_from_bytes(encoded)
			assert i == decoded


class TestJson :

	def test_JsonStream(self) :
		# arrange
		date = datetime.now(timezone.utc)
		guid = uuid4()
		user = KhUser(3, AuthToken(3, date, guid, { 'some': 'data' }, 'token'), set([Scope.user]))
		data = (1, '2', date, (1, 2), { 'a': 1, 'b': (2,), 3: 4 }, { 1, 2, 3 }, AnEnum.value_a, user)
		expected = [1, '2', str(date), [1, 2], { 'a': 1, 'b': [2], '3': 4 }, [1, 2, 3], 'value_a', { 'user_id': 3, 'scope': ['user'], 'token': { 'expires': str(date), 'guid': guid.hex, 'data': { 'some': 'data' } } }]

		# act
		result = json_stream(data)

		# assert
		assert expected == result


class TestTerminated :

	def test_TerminatedHandlesSigterm(self) :
		assert Terminated.alive == True

		kill(getpid(), SIGTERM)

		assert Terminated.alive == False
