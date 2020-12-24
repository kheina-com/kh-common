from kh_common.utilities import int_from_bytes, int_to_bytes


class TestInit :

	def int_generator(self) :
		for i in range(100) :
			yield int('1' + '0' * i)


	def test_IntBytesConverters(self) :
		for i in self.int_generator() :
			encoded = int_to_bytes(i)
			decoded = int_from_bytes(encoded)
			assert i == decoded
