from asyncio import Lock
from collections import OrderedDict
from copy import copy
from time import time
from typing import Any, Dict, Iterable, List, Set, Tuple
from concurrent.futures import ThreadPoolExecutor
from asyncio import get_event_loop
from functools import partial, wraps

import aerospike

from kh_common.config.constants import environment
from kh_common.utilities import __clear_cache__


class KeyValueStore :

	_client = None

	def __init__(self: 'KeyValueStore', namespace: str, set: str, local_TTL: float = 1) :
		if not KeyValueStore._client and not environment.is_test() :
			from kh_common.config.credentials import aerospike as config
			config['hosts'] = list(map(tuple, config['hosts']))
			KeyValueStore._client = aerospike.client(config).connect()

		self._cache: OrderedDict = OrderedDict()
		self._local_TTL: float = local_TTL
		self._namespace: str = namespace
		self._set: str = set
		self._get_lock: Lock = Lock()
		self._get_many_lock: Lock = Lock()


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


	@wraps(put)
	async def put_async(self: 'KeyValueStore', *args, **kwargs) :
		with ThreadPoolExecutor() as threadpool :
			return await get_event_loop().run_in_executor(threadpool, partial(self.put, *args, **kwargs))


	def _get(self: 'KeyValueStore', key: str) :
		if key in self._cache :
			return copy(self._cache[key][1])

		_, _, data = KeyValueStore._client.get((self._namespace, self._set, key))
		self._cache[key] = (time() + self._local_TTL, data['data'])

		return copy(data['data'])


	def get(self: 'KeyValueStore', key: str) -> Any :
		__clear_cache__(self._cache, time)
		return self._get(key)


	@wraps(get)
	async def get_async(self: 'KeyValueStore', *args, **kwargs) :
		async with self._get_lock :
			with ThreadPoolExecutor() as threadpool :
				return await get_event_loop().run_in_executor(threadpool, partial(self.get, *args, **kwargs))


	def _get_many(self: 'KeyValueStore', keys: Iterable[str]) :
		keys: Set[str] = set(keys)
		remote_keys: Set[str] = keys - self._cache.keys()

		if remote_keys :
			data: List[Tuple[Any]] = KeyValueStore._client.get_many(list(map(lambda k : (self._namespace, self._set, k), remote_keys)))
			data_map: Dict[str, Any] = { }

			exp: float = time() + self._local_TTL
			for datum in data :
				key: str = datum[0][2]

				# filter on the metadata, since it will always be populated
				if datum[1] :
					value: Any = datum[2]['data']
					data_map[key] = copy(value)
					self._cache[key] = (exp, value)

				else :
					data_map[key] = None

			return {
				**data_map,
				**{
					key: copy(self._cache[key][1])
					for key in keys - remote_keys
				},
			}

		# only local cache is required
		return {
			key: self._cache[key][1]
			for key in keys
		}


	def get_many(self: 'KeyValueStore', keys: Iterable[str]) -> Dict[str, Any] :
		__clear_cache__(self._cache, time)
		return self._get_many(keys)


	@wraps(get_many)
	async def get_many_async(self: 'KeyValueStore', *args, **kwargs) :
		async with self._get_many_lock :
			with ThreadPoolExecutor() as threadpool :
				return await get_event_loop().run_in_executor(threadpool, partial(self.get_many, *args, **kwargs))


	def remove(self: 'KeyValueStore', key: str) -> None :
		if key in self._cache :
			del self._cache[key]

		self._client.remove(
			(self._namespace, self._set, key),
			policy={
				'max_retries': 3,
			},
		)


	@wraps(remove)
	async def remove_async(self: 'KeyValueStore', *args, **kwargs) :
		with ThreadPoolExecutor() as threadpool :
			return await get_event_loop().run_in_executor(threadpool, partial(self.remove, *args, **kwargs))


	def exists(self: 'KeyValueStore', key: str) -> bool :
		try :
			_, meta = self._client.exists(
				(self._namespace, self._set, key),
				policy={
					'max_retries': 3,
				},
			)
			# check the metadata, since it will always be populated
			return meta != None

		except aerospike.exception.RecordNotFound :
			return False


	@wraps(exists)
	async def exists_async(self: 'KeyValueStore', *args, **kwargs) :
		with ThreadPoolExecutor() as threadpool :
			return await get_event_loop().run_in_executor(threadpool, partial(self.exists, *args, **kwargs))


	def truncate(self: 'KeyValueStore') -> None :
		self._client.truncate(self._namespace, self._set, 0)
