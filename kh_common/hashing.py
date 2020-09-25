from kh_common import getFullyQualifiedClassName
from hashlib import sha1


class Hashable :

	_hash = 0

	def __init__(self) :
		name = f"<class '{getFullyQualifiedClassName(self)}' {Hashable._hash}>"
		self.hash = int.from_bytes(sha1(name.encode()).digest(), 'big')
		Hashable._hash += 1


	def __hash__(self) :
		return self.hash
