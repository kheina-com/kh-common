from kh_common.utilities import getFullyQualifiedClassName


class Hashable :

	_hash = 0

	def __init__(self) :
		self._hash = hash(f"<class '{getFullyQualifiedClassName(self)}' {Hashable._hash}>")
		Hashable._hash += 1


	def __hash__(self) :
		return self._hash
