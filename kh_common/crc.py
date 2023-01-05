class CRC :

	def __init__(self: 'CRC', bit_length: int = 32, polynomial: int = 0x04c11db7, init_value: int = None, xor_out: int = None) -> 'CRC' :
		if int(bit_length / 8) != float(bit_length / 8) :
			raise ValueError('bit_length must be an integer and divisible by 8')

		self.bitlength = int(bit_length)
		self.polynomial = int(polynomial)
		self.bitmask = 2 ** self.bitlength - 1
		self.init_value = int(init_value) if init_value is not None else self.bitmask
		self.xor_out = int(xor_out) if xor_out is not None else self.bitmask

		i = 1
		crc = msbMask = 0x01 << (self.bitlength - 1)
		table = [0] * 256

		while i < 256 :
			if crc & msbMask :
				crc = (crc << 1) ^ polynomial
			else :
				crc <<= 1

			# & bitmask is required to ensure python doesn't expand the variable beyond bitlength bits
			crc &= self.bitmask

			for j in range(i) :
				table[i + j] = (crc ^ table[j])

			i <<= 1
		
		self.table = tuple(table)


	def __call__(self: 'CRC', value: bytes) -> int :
		crc = self.init_value

		for i in value :
			# iterating over bytes automatically converts to ints
			# & bitmask is required to ensure python doesn't expand the variable beyond bitlength bits
			crc = self.table[i ^ ((crc >> (self.bitlength - 8)) & 0xff)] ^ ((crc << 8) & self.bitmask)

		return crc ^ self.xor_out
