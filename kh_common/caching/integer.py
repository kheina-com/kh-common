from kh_common.caching import __clear_cache__
from collections import OrderedDict
from typing import Any, Tuple
from copy import copy
from time import time
import aerospike


_client = None


if not _client :
	from kh_common.config.credentials import aerospike as config
	config['hosts'] = list(map(tuple, config['hosts']))
	_client = aerospike.client(config).connect()


class Integer :

	def __init__(self: 'Integer', namespace: str, set: str, key: str, local_TTL: float = 1) :
		self._key: Tuple[str] = (namespace, set, key)
		self._cache: OrderedDict = OrderedDict()
		self._local_TTL: float = local_TTL


	def set(self: 'Integer',  value: int, TTL: int = 0) :
		_client.put(
			self._key,
			{ 'int': value },
			meta={
				'ttl': TTL,
			},
			policy={
				'max_retries': 3,
			},
		)
		self._cache[self._key[-1]] = (time() + self._local_TTL, value)


	def get(self: 'Integer') :
		__clear_cache__(self._cache)

		if self._key[-1] in self._cache :
			return copy(self._cache[self._key[-1]][1])

		_, _, data = _client.get(self._key)
		self._cache[self._key[-1]] = (time() + self._local_TTL, data['int'])

		return data['int']


	def increment(self: 'Integer',  value: int = 1, TTL: int = 0) :
		_client.increment(
			self._key,
			'int',
			value,
			meta={
				'ttl': TTL,
			},
			policy={
				'max_retries': 3,
			},
		)
