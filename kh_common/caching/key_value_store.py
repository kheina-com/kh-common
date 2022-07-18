from kh_common.utilities import __clear_cache__
from collections import OrderedDict
from asyncio import Lock
from typing import Any
from copy import copy
from time import time
import aerospike


class KeyValueStore :

	_client = None

	def __init__(self: 'KeyValueStore', namespace: str, set: str, local_TTL: float = 1) :
		if not KeyValueStore._client :
			from kh_common.config.credentials import aerospike as config
			config['hosts'] = list(map(tuple, config['hosts']))
			KeyValueStore._client = aerospike.client(config).connect()

		self._cache: OrderedDict = OrderedDict()
		self._local_TTL: float = local_TTL
		self._namespace: str = namespace
		self._set: str = set
		self._lock: Lock = Lock()


	def put(self: 'KeyValueStore', key: str, data: Any, TTL: int = 0) :
		KeyValueStore._client.put(
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


	def _get(self: 'KeyValueStore', key: str) :
		if key in self._cache :
			return copy(self._cache[key][1])

		_, _, data = KeyValueStore._client.get((self._namespace, self._set, key))
		self._cache[key] = (time() + self._local_TTL, data['data'])

		return data['data']


	def get(self: 'KeyValueStore', key: str) :
		__clear_cache__(self._cache, time)
		return self._get(key)


	async def get_async(self: 'KeyValueStore', key: str) :
		async with self._lock :
			__clear_cache__(self._cache, time)
		return self._get(key)
