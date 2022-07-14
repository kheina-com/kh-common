from kh_common.caching import __clear_cache__
from collections import OrderedDict
from typing import Any
from copy import copy
from time import time
import aerospike


_client = None


if not _client :
	from kh_common.config.credentials import aerospike as config
	config['hosts'] = list(map(tuple, config['hosts']))
	_client = aerospike.client(config).connect()


class KeyValueStore :

	def __init__(self: 'KeyValueStore', namespace: str, set: str, local_TTL: float = 1) :
		self._cache: OrderedDict = OrderedDict()
		self._local_TTL: float = local_TTL
		self._namespace: str = namespace
		self._set: str = set


	def put(self: 'KeyValueStore', key: str, data: Any, TTL: int = 0) :
		_client.put(
			(self._namespace, self._set, key),
			{ 'data': data },
			meta={
				'ttl': TTL,
			},
			policy={
				'max_retries': 3,
			},
		)
		self._cache[key] = (time() + self._local_TTL, data)


	def get(self: 'KeyValueStore', key: str) :
		__clear_cache__(self._cache)

		if key in self._cache :
			return copy(self._cache[key][1])

		_, _, data = _client.get((self._namespace, self._set, key))
		self._cache[key] = (time() + self._local_TTL, data['data'])

		return data['data']
