from kh_common.utilities import __clear_cache__
from collections import OrderedDict
from asyncio import Lock
from typing import Tuple
from copy import copy
from time import time
import aerospike


class Integer :

	_client = None

	def __init__(self: 'Integer', namespace: str, set: str, key: str, local_TTL: float = 1) :
		if not Integer._client :
			from kh_common.config.credentials import aerospike as config
			config['hosts'] = list(map(tuple, config['hosts']))
			Integer._client = aerospike.client(config).connect()

		self._key: Tuple[str] = (namespace, set, key)
		self._cache: OrderedDict = OrderedDict()
		self._local_TTL: float = local_TTL
		self._lock: Lock = Lock()


	def set(self: 'Integer', value: int, TTL: int = 0) -> None :
		Integer._client.put(
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


	def _get(self: 'Integer') -> int :
		if self._key[-1] in self._cache :
			return copy(self._cache[self._key[-1]][1])

		_, _, data = Integer._client.get(self._key)
		self._cache[self._key[-1]] = (time() + self._local_TTL, data['int'])

		return data['int']


	def get(self: 'Integer') -> int :
		__clear_cache__(self._cache, time)
		return self._get()


	async def get_async(self: 'Integer') -> int :
		async with self._lock :
			__clear_cache__(self._cache, time)
		return self._get()


	def increment(self: 'Integer', value: int = 1, TTL: int = 0) -> None :
		Integer._client.increment(
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
