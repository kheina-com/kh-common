from kh_common.utilities import getFullyQualifiedClassName, int_from_bytes
from hashlib import sha1


class Hashable :

	_hash = 0

	def __init__(self) :
		name = f"<class '{getFullyQualifiedClassName(self)}' {Hashable._hash}>"
		self._hash = int_from_bytes(sha1(name.encode()).digest())
		Hashable._hash += 1


	def __hash__(self) :
		return self._hash
