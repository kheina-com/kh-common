from kh_common.utilities import int_from_bytes, int_to_bytes
from kh_common.utilities.json import json_stream
from datetime import datetime


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
		date = datetime.now()
		data = (1, '2', date, (1, 2), { 'a': 1, 'b': (1,) }, { 1, 2, 3 })
		expected = [1, '2', date.timestamp(), [1, 2], { 'a': 1, 'b': [1] }, [1, 2, 3]]

		# act
		result = json_stream(data)

		# assert
		assert expected == result
