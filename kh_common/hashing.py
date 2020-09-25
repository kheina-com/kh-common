from hashlib import sha1
from math import ceil


class Hashable :

	_hash = 0

	def __init__(self) :
		name = f"<class '{self.__class__.__name__}' {Hashable._hash}>"
		self.hash = int.from_bytes(sha1(name.encode()).digest(), 'big')
		Hashable._hash += 1


	def __hash__(self) :
		return self.hash
