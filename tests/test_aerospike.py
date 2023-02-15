from kh_common.logging import LogHandler; LogHandler.logging_available = False
import time

import pytest

from kh_common.caching import AerospikeCache
from kh_common.caching.integer import Integer
from kh_common.caching.key_value_store import KeyValueStore
from tests.utilities.aerospike import AerospikeClient
from tests.utilities.caching import CachingTestClass


class TestAerospikeCache(CachingTestClass) :

	it = 0
	client = None

	def setup(self) :
		TestAerospikeCache.client = AerospikeClient()
		KeyValueStore._client = TestAerospikeCache.client
		Integer._client = TestAerospikeCache.client


	def test_AerospikeCache_int(self) :
		# setup
		TestAerospikeCache.client.clear()
		TestAerospikeCache.it = 0

		@AerospikeCache('kheina', 'test', '{t}.{a}', 0, local_TTL=5)
		def cache_test(t, a=2) -> int :
			TestAerospikeCache.it += 1
			return t + TestAerospikeCache.it - 1

		# assert
		# set
		assert 1 == cache_test(1)
		assert 3 == cache_test(2, a=2)
		assert 5 == cache_test(3, **{ 'a': 2 })

		# local cache
		assert 1 == cache_test(1)
		assert 3 == cache_test(2)
		assert 5 == cache_test(3)

		# aerospike cache
		assert 1 == cache_test(1)
		assert 3 == cache_test(2)
		assert 5 == cache_test(3)

		# check cache
		assert 3 == len(TestAerospikeCache.client.calls['put'])
		assert 6 == len(TestAerospikeCache.client.calls['get'])  # initial set runs get + aerospike retrieval

		# purge
		TestAerospikeCache.client.clear()

		# local cache again
		assert 1 == cache_test(1)
		assert 3 == cache_test(2)
		assert 5 == cache_test(3)

		# reset
		assert 4 == cache_test(1)
		assert 6 == cache_test(2)
		assert 8 == cache_test(3)

		assert 3 == len(TestAerospikeCache.client.calls['put'])
		assert 3 == len(TestAerospikeCache.client.calls['get'])


	def test_AerospikeCache_IncorrectType(self) :

		# arrange
		# we gotta inject a value with an incorrect return type
		TestAerospikeCache.client.put(('kheina', 'test', 'value'), { 'data': 1 })
		TestAerospikeCache.client.clear()
		TestAerospikeCache.it = 0

		@AerospikeCache('kheina', 'test', '{v}', local_TTL=0)
		def cache_test(v) -> str :
			TestAerospikeCache.it += 1
			return v

		# apply
		assert 'value' == cache_test('value')

		# assert
		assert 1 == TestAerospikeCache.it
		assert 1 == len(TestAerospikeCache.client.calls['put'])
		assert 1 == len(TestAerospikeCache.client.calls['get'])
		assert { 'data': 'value' } == TestAerospikeCache.client.get(('kheina', 'test', 'value'))[2]


@pytest.mark.asyncio
class TestAerospikeCacheAsync(CachingTestClass) :

	it = 0

	async def test_async_AerospikeCache_int(self) :
		# setup
		TestAerospikeCache.client.clear()
		TestAerospikeCache.it = 0

		@AerospikeCache('kheina', 'test', '{t}.{a}', 0, local_TTL=5)
		async def cache_test(t, a=2, b=1) -> int :
			TestAerospikeCache.it += 1
			return t + TestAerospikeCache.it - 1

		# assert
		# set
		assert 1 == await cache_test(1)
		assert 3 == await cache_test(2, a=2)
		assert 5 == await cache_test(3, **{ 'a': 2 })

		# local cache
		assert 1 == await cache_test(1)
		assert 3 == await cache_test(2)
		assert 5 == await cache_test(3)

		# aerospike cache
		assert 1 == await cache_test(1)
		assert 3 == await cache_test(2)
		assert 5 == await cache_test(3)

		# check cache
		assert 3 == len(TestAerospikeCache.client.calls['put'])
		assert 6 == len(TestAerospikeCache.client.calls['get'])  # initial set runs get + aerospike retrieval

		# purge
		TestAerospikeCache.client.clear()

		# local cache again
		assert 1 == await cache_test(1)
		assert 3 == await cache_test(2)
		assert 5 == await cache_test(3)

		# reset
		assert 4 == await cache_test(1)
		assert 6 == await cache_test(2)
		assert 8 == await cache_test(3)

		assert 3 == len(TestAerospikeCache.client.calls['put'])
		assert 3 == len(TestAerospikeCache.client.calls['get'])  # initial set runs get + aerospike retrieval


	async def test_async_AerospikeCache_IncorrectType(self) :

		# arrange
		# we gotta inject a value with an incorrect return type
		TestAerospikeCache.client.put(('kheina', 'test', 'value'), { 'data': 1 })
		TestAerospikeCache.client.clear()
		TestAerospikeCache.it = 0

		@AerospikeCache('kheina', 'test', '{v}', local_TTL=0)
		async def cache_test(v) -> str :
			TestAerospikeCache.it += 1
			return v

		# apply
		assert 'value' == await cache_test('value')

		# assert
		assert 1 == TestAerospikeCache.it
		assert 1 == len(TestAerospikeCache.client.calls['put'])
		assert 1 == len(TestAerospikeCache.client.calls['get'])
		assert { 'data': 'value' } == TestAerospikeCache.client.get(('kheina', 'test', 'value'))[2]


class TestKeyValueStore :

	def test_Get_LocalCacheEmpty_ClientReturnsValue(self) :

		# arrange
		key = 'key'
		data = 1

		TestAerospikeCache.client.clear()
		TestAerospikeCache.client.put(('kheina', 'test', key), { 'data': data })
		TestAerospikeCache.client.calls.clear()

		kvs = KeyValueStore('kheina', 'test')

		# apply
		result = kvs.get(key)

		# assert
		assert result == data
		assert len(TestAerospikeCache.client.calls['get']) == 1


	def test_Get_LocalCachePopulated_ClientNotCalled(self) :

		# arrange
		key = 'key'
		data = 1

		TestAerospikeCache.client.clear()
		TestAerospikeCache.client.put(('kheina', 'test', key), { 'data': data })
		TestAerospikeCache.client.calls.clear()

		kvs = KeyValueStore('kheina', 'test')

		# apply
		result = kvs.put(key, data)
		result = kvs.get(key)

		# assert
		assert result == data
		assert len(TestAerospikeCache.client.calls['get']) == 0


	def test_Get_LocalCacheCleaned_ClientReturnsValue(self) :

		# arrange
		key = 'key'
		data = 1

		TestAerospikeCache.client.clear()
		TestAerospikeCache.client.put(('kheina', 'test', key), { 'data': data })
		TestAerospikeCache.client.calls.clear()

		kvs = KeyValueStore('kheina', 'test')
		kvs._cache[key] = (time.time(), data)

		# apply
		result = kvs.get(key)

		# assert
		assert result == data
		assert len(TestAerospikeCache.client.calls['get']) == 1


	def test_Get_LocalTTLZero_LocalCacheNotUsed(self) :

		# arrange
		key = 'key'
		data = 1

		TestAerospikeCache.client.clear()
		TestAerospikeCache.client.put(('kheina', 'test', key), { 'data': data })
		TestAerospikeCache.client.calls.clear()

		kvs = KeyValueStore('kheina', 'test', local_TTL=0)

		# apply
		result = kvs.get(key)
		result = kvs.get(key)

		# assert
		assert result == data
		assert len(TestAerospikeCache.client.calls['get']) == 2


	def test_Put_CacheEmpty_CacheCalledCorrectly(self) :

		# arrange
		key = 'key'
		data = 1

		TestAerospikeCache.client.clear()

		kvs = KeyValueStore('kheina', 'test', local_TTL=0)

		# apply
		kvs.put(key, data)
		result = kvs.get(key)

		# assert
		assert result == data
		assert len(TestAerospikeCache.client.calls['put']) == 1
		assert len(TestAerospikeCache.client.calls['get']) == 1
		assert TestAerospikeCache.client.calls['put'][0] == (('kheina', 'test', key), { 'data': data }, { 'ttl': 0 }, { 'max_retries': 3 })


	def test_Put_TTLSet_CacheCalledCorrectly(self) :

		# arrange
		key = 'key'
		data = 1

		TestAerospikeCache.client.clear()

		kvs = KeyValueStore('kheina', 'test', local_TTL=0)

		# apply
		kvs.put(key, data, TTL=1000)
		result = kvs.get(key)

		# assert
		assert result == data
		assert len(TestAerospikeCache.client.calls['put']) == 1
		assert len(TestAerospikeCache.client.calls['get']) == 1
		assert TestAerospikeCache.client.calls['put'][0] == (('kheina', 'test', key), { 'data': data }, { 'ttl': 1000 }, { 'max_retries': 3 })


	def test_Put_CachePopulated_CacheOverWritten(self) :

		# arrange
		key = 'key'
		different_data = 10
		data = 1

		TestAerospikeCache.client.clear()

		kvs = KeyValueStore('kheina', 'test', local_TTL=0)

		# apply
		kvs.put(key, data)
		kvs.put(key, different_data)
		result = kvs.get(key)

		# assert
		assert result == different_data
		assert len(TestAerospikeCache.client.calls['put']) == 2
		assert len(TestAerospikeCache.client.calls['get']) == 1
		assert TestAerospikeCache.client.calls['put'][-1] == (('kheina', 'test', key), { 'data': different_data }, { 'ttl': 0 }, { 'max_retries': 3 })


	def test_GetMany_HalfLocalHalfRemotePopulated_AllValuesReturned(self) :

		# arrange
		TestAerospikeCache.client.clear()
		kvs = KeyValueStore('kheina', 'test')
		keys = [f'key.{i}' for i in range(10)]
		values = [(key, i) for i, key in enumerate(keys)]

		for key, i in values[:5] :
			kvs.put(key, i)

		kvs = KeyValueStore('kheina', 'test')

		for key, i in values[5:] :
			kvs.put(key, i)

		# apply
		results = kvs.get_many(keys)

		# assert
		assert results == {
			key: i
			for i, key in enumerate(keys)
		}
		assert len(kvs._cache) == len(keys)
		assert len(TestAerospikeCache.client.calls['get']) == 0
		assert len(TestAerospikeCache.client.calls['get_many']) == 1
		# only the keys not held in local cache were called
		assert set(TestAerospikeCache.client.calls['get_many'][0][0]) == set(('kheina', 'test', key) for key in keys[:5])


	def test_GetMany_RemotePopulated_AllValuesReturned(self) :

		# arrange
		TestAerospikeCache.client.clear()
		kvs = KeyValueStore('kheina', 'test')
		keys = [f'key.{i}' for i in range(10)]
		values = [(key, i) for i, key in enumerate(keys)]

		for key, i in values :
			kvs.put(key, i)

		kvs = KeyValueStore('kheina', 'test')

		# apply
		results = kvs.get_many(keys)

		# assert
		assert results == {
			key: i
			for i, key in enumerate(keys)
		}
		assert len(TestAerospikeCache.client.calls['get']) == 0
		assert len(TestAerospikeCache.client.calls['get_many']) == 1
		# only the keys not held in local cache were called
		assert set(TestAerospikeCache.client.calls['get_many'][0][0]) == set(('kheina', 'test', key) for key in keys)


	def test_GetMany_LocalPopulated_AllValuesReturned(self) :

		# arrange
		TestAerospikeCache.client.clear()
		kvs = KeyValueStore('kheina', 'test')
		keys = [f'key.{i}' for i in range(10)]
		values = [(key, i) for i, key in enumerate(keys)]

		for key, i in values :
			kvs.put(key, i)

		# apply
		results = kvs.get_many(keys)

		# assert
		assert results == {
			key: i
			for i, key in enumerate(keys)
		}
		assert len(TestAerospikeCache.client.calls['get']) == 0
		assert len(TestAerospikeCache.client.calls['get_many']) == 0


	def test_Remove_LocalPopulated_RecordRemoved(self) :

		# arrange
		TestAerospikeCache.client.clear()
		kvs = KeyValueStore('kheina', 'test')
		key = 'key'
		data = 1

		# apply
		kvs.put(key, data)
		kvs.remove(key)

		# assert
		assert len(TestAerospikeCache.client.calls['remove']) == 1
		assert TestAerospikeCache.client.calls['remove'][0] == (('kheina', 'test', key), None, { 'max_retries': 3 })
		assert key not in kvs._cache


	def test_Exists_LocalPopulated_KeyExistsReturnsTrue(self) :

		# arrange
		TestAerospikeCache.client.clear()
		kvs = KeyValueStore('kheina', 'test')
		key = 'key'
		data = 0

		# apply
		kvs.put(key, data)
		result = kvs.exists(key)

		# assert
		assert result == True
		assert len(TestAerospikeCache.client.calls['exists']) == 1
		assert TestAerospikeCache.client.calls['exists'][0] == (('kheina', 'test', key), None, { 'max_retries': 3 })


	def test_Exists_LocalNotPopulated_KeyExistsReturnsFalse(self) :

		# arrange
		TestAerospikeCache.client.clear()
		kvs = KeyValueStore('kheina', 'test')
		key = 'key'

		# apply
		result = kvs.exists(key)

		# assert
		assert result == False
		assert len(TestAerospikeCache.client.calls['exists']) == 1
		assert TestAerospikeCache.client.calls['exists'][0] == (('kheina', 'test', key), None, { 'max_retries': 3 })


	def test_Get_EnsureCacheNotModified_CacheUnchanged(self) :

		# arrange
		TestAerospikeCache.client.clear()
		kvs = KeyValueStore('kheina', 'test')
		key = 'key'
		data = { 'a': 1, 'b': '2', 'c': 3.1 }

		kvs.put(key, data)
		# wipe local cache
		kvs._cache.clear()

		# apply
		kvs.get(key).pop('a')

		# assert
		assert data == kvs.get(key)


	def test_GetMany_NotAllKeysExist_EmptyKeysReturnNone(self) :

		# arrange
		TestAerospikeCache.client.clear()
		kvs = KeyValueStore('kheina', 'test')
		keys = ['key1', 'key2', 'key3']

		# apply
		results = kvs.get_many(keys)

		# assert
		assert len(results) == len(keys)
		assert results == { k: None for k in keys }


@pytest.mark.asyncio
class TestKeyValueStoreAsync :

	async def test_GetAsync_LocalCacheEmpty_ClientReturnsValue(self) :

		# arrange
		key = 'key'
		data = 1

		TestAerospikeCache.client.clear()
		TestAerospikeCache.client.put(('kheina', 'test', key), { 'data': data })
		TestAerospikeCache.client.calls.clear()

		kvs = KeyValueStore('kheina', 'test')

		# apply
		result = await kvs.get_async(key)

		# assert
		assert result == data
		assert len(TestAerospikeCache.client.calls['get']) == 1


	async def test_GetAsync_LocalCachePopulated_ClientNotCalled(self) :

		# arrange
		key = 'key'
		data = 1

		TestAerospikeCache.client.clear()
		TestAerospikeCache.client.put(('kheina', 'test', key), { 'data': data })
		TestAerospikeCache.client.calls.clear()

		kvs = KeyValueStore('kheina', 'test')

		# apply
		result = await kvs.put_async(key, data)
		result = await kvs.get_async(key)

		# assert
		assert result == data
		assert len(TestAerospikeCache.client.calls['get']) == 0


	async def test_GetAsync_LocalCacheCleaned_ClientReturnsValue(self) :

		# arrange
		key = 'key'
		data = 1

		TestAerospikeCache.client.clear()
		TestAerospikeCache.client.put(('kheina', 'test', key), { 'data': data })
		TestAerospikeCache.client.calls.clear()

		kvs = KeyValueStore('kheina', 'test')
		kvs._cache[key] = (time.time(), data)

		# apply
		result = await kvs.get_async(key)

		# assert
		assert result == data
		assert len(TestAerospikeCache.client.calls['get']) == 1


	async def test_GetAsync_LocalTTLZero_LocalCacheNotUsed(self) :

		# arrange
		key = 'key'
		data = 1

		TestAerospikeCache.client.clear()
		TestAerospikeCache.client.put(('kheina', 'test', key), { 'data': data })
		TestAerospikeCache.client.calls.clear()

		kvs = KeyValueStore('kheina', 'test', local_TTL=0)

		# apply
		result = await kvs.get_async(key)
		result = await kvs.get_async(key)

		# assert
		assert result == data
		assert len(TestAerospikeCache.client.calls['get']) == 2


	async def test_PutAsync_CacheEmpty_CacheCalledCorrectly(self) :

		# arrange
		key = 'key'
		data = 1

		TestAerospikeCache.client.clear()

		kvs = KeyValueStore('kheina', 'test', local_TTL=0)

		# apply
		await kvs.put_async(key, data)
		result = await kvs.get_async(key)

		# assert
		assert result == data
		assert len(TestAerospikeCache.client.calls['put']) == 1
		assert len(TestAerospikeCache.client.calls['get']) == 1
		assert TestAerospikeCache.client.calls['put'][0] == (('kheina', 'test', key), { 'data': data }, { 'ttl': 0 }, { 'max_retries': 3 })


	async def test_PutAsync_TTLSet_CacheCalledCorrectly(self) :

		# arrange
		key = 'key'
		data = 1

		TestAerospikeCache.client.clear()

		kvs = KeyValueStore('kheina', 'test', local_TTL=0)

		# apply
		await kvs.put_async(key, data, TTL=1000)
		result = await kvs.get_async(key)

		# assert
		assert result == data
		assert len(TestAerospikeCache.client.calls['put']) == 1
		assert len(TestAerospikeCache.client.calls['get']) == 1
		assert TestAerospikeCache.client.calls['put'][0] == (('kheina', 'test', key), { 'data': data }, { 'ttl': 1000 }, { 'max_retries': 3 })


	async def test_PutAsync_CachePopulated_CacheOverWritten(self) :

		# arrange
		key = 'key'
		different_data = 10
		data = 1

		TestAerospikeCache.client.clear()

		kvs = KeyValueStore('kheina', 'test', local_TTL=0)

		# apply
		await kvs.put_async(key, data)
		await kvs.put_async(key, different_data)
		result = await kvs.get_async(key)

		# assert
		assert result == different_data
		assert len(TestAerospikeCache.client.calls['put']) == 2
		assert len(TestAerospikeCache.client.calls['get']) == 1
		assert TestAerospikeCache.client.calls['put'][-1] == (('kheina', 'test', key), { 'data': different_data }, { 'ttl': 0 }, { 'max_retries': 3 })


	async def test_GetManyAsync_HalfLocalHalfRemotePopulated_AllValuesReturned(self) :

		# arrange
		TestAerospikeCache.client.clear()
		kvs = KeyValueStore('kheina', 'test')
		keys = [f'key.{i}' for i in range(10)]
		values = [(key, i) for i, key in enumerate(keys)]

		for key, i in values[:5] :
			await kvs.put_async(key, i)

		kvs = KeyValueStore('kheina', 'test')

		for key, i in values[5:] :
			await kvs.put_async(key, i)

		# apply
		results = await kvs.get_many_async(keys)

		# assert
		assert results == {
			key: i
			for i, key in enumerate(keys)
		}
		assert len(kvs._cache) == len(keys)
		assert len(TestAerospikeCache.client.calls['get']) == 0
		assert len(TestAerospikeCache.client.calls['get_many']) == 1
		# only the keys not held in local cache were called
		assert set(TestAerospikeCache.client.calls['get_many'][0][0]) == set(('kheina', 'test', key) for key in keys[:5])


	async def test_GetManyAsync_RemotePopulated_AllValuesReturned(self) :

		# arrange
		TestAerospikeCache.client.clear()
		kvs = KeyValueStore('kheina', 'test')
		keys = [f'key.{i}' for i in range(10)]
		values = [(key, i) for i, key in enumerate(keys)]

		for key, i in values :
			await kvs.put_async(key, i)

		kvs = KeyValueStore('kheina', 'test')

		# apply
		results = await kvs.get_many_async(keys)

		# assert
		assert results == {
			key: i
			for i, key in enumerate(keys)
		}
		assert len(TestAerospikeCache.client.calls['get']) == 0
		assert len(TestAerospikeCache.client.calls['get_many']) == 1
		# only the keys not held in local cache were called
		assert set(TestAerospikeCache.client.calls['get_many'][0][0]) == set(('kheina', 'test', key) for key in keys)


	async def test_GetManyAsync_LocalPopulated_AllValuesReturned(self) :

		# arrange
		TestAerospikeCache.client.clear()
		kvs = KeyValueStore('kheina', 'test')
		keys = [f'key.{i}' for i in range(10)]
		values = [(key, i) for i, key in enumerate(keys)]

		for key, i in values :
			await kvs.put_async(key, i)

		# apply
		results = await kvs.get_many_async(keys)

		# assert
		assert results == {
			key: i
			for i, key in enumerate(keys)
		}
		assert len(TestAerospikeCache.client.calls['get']) == 0
		assert len(TestAerospikeCache.client.calls['get_many']) == 0


	async def test_RemoveAsync_LocalPopulated_RecordRemoved(self) :

		# arrange
		TestAerospikeCache.client.clear()
		kvs = KeyValueStore('kheina', 'test')
		key = 'key'
		data = 1

		# apply
		await kvs.put_async(key, data)
		await kvs.remove_async(key)

		# assert
		assert len(TestAerospikeCache.client.calls['remove']) == 1
		assert TestAerospikeCache.client.calls['remove'][0] == (('kheina', 'test', key), None, { 'max_retries': 3 })
		assert key not in kvs._cache


	async def test_ExistsAsync_LocalPopulated_KeyExistsReturnsTrue(self) :

		# arrange
		TestAerospikeCache.client.clear()
		kvs = KeyValueStore('kheina', 'test')
		key = 'key'
		data = 0

		# apply
		await kvs.put_async(key, data)
		result = await kvs.exists_async(key)

		# assert
		assert result == True
		assert len(TestAerospikeCache.client.calls['exists']) == 1
		assert TestAerospikeCache.client.calls['exists'][0] == (('kheina', 'test', key), None, { 'max_retries': 3 })


	async def test_ExistsAsync_LocalNotPopulated_KeyExistsReturnsFalse(self) :

		# arrange
		TestAerospikeCache.client.clear()
		kvs = KeyValueStore('kheina', 'test')
		key = 'key'

		# apply
		result = await kvs.exists_async(key)

		# assert
		assert result == False
		assert len(TestAerospikeCache.client.calls['exists']) == 1
		assert TestAerospikeCache.client.calls['exists'][0] == (('kheina', 'test', key), None, { 'max_retries': 3 })


	async def test_GetAsync_EnsureCacheNotModified_CacheUnchanged(self) :

		# arrange
		TestAerospikeCache.client.clear()
		kvs = KeyValueStore('kheina', 'test')
		key = 'key'
		data = { 'a': 1, 'b': '2', 'c': 3.1 }

		await kvs.put_async(key, data)
		# wipe local cache
		kvs._cache.clear()

		# apply
		result = await kvs.get_async(key)
		result.pop('a')

		# assert
		assert data == await kvs.get_async(key)


	async def test_GetManyAsync_NotAllKeysExist_EmptyKeysReturnNone(self) :

		# arrange
		TestAerospikeCache.client.clear()
		kvs = KeyValueStore('kheina', 'test')
		keys = ['key1', 'key2', 'key3']

		# apply
		results = await kvs.get_many_async(keys)

		# assert
		assert len(results) == len(keys)
		assert results == { k: None for k in keys }


class TestInteger :

	def test_set_CacheEmpty_LocalCachePopulated(self) :

		# arrange
		TestAerospikeCache.client.clear()

		data = 100

		i = Integer('kheina', 'test', 'an_int')

		# apply
		i.set(data)
		result = i.get()

		# assert
		assert result == data
		assert len(TestAerospikeCache.client.calls['put']) == 1
		assert len(TestAerospikeCache.client.calls['get']) == 0


	def test_set_CacheEmpty_AerospikeCachePopulated(self) :

		# arrange
		TestAerospikeCache.client.clear()

		data = 100

		i = Integer('kheina', 'test', 'an_int', local_TTL=0)

		# apply
		i.set(data)
		result = i.get()

		# assert
		assert result == data
		assert len(TestAerospikeCache.client.calls['put']) == 1
		assert len(TestAerospikeCache.client.calls['get']) == 1


	def test_increment_CachePopulated_CacheIncrement(self) :

		# arrange
		TestAerospikeCache.client.clear()

		data = 100

		i = Integer('kheina', 'test', 'an_int', local_TTL=0)

		# apply
		i.set(data)
		i.increment()
		result = i.get()

		# assert
		assert result == data + 1
		assert len(TestAerospikeCache.client.calls['put']) == 1
		assert len(TestAerospikeCache.client.calls['increment']) == 1
		assert len(TestAerospikeCache.client.calls['get']) == 1


	def test_increment_CachePopulated_CacheIncrementMany(self) :

		# arrange
		TestAerospikeCache.client.clear()

		data = 100

		i = Integer('kheina', 'test', 'an_int', local_TTL=0)

		# apply
		i.set(data)
		i.increment(11)
		i.increment(-7)
		result = i.get()

		# assert
		assert result == 104
		assert len(TestAerospikeCache.client.calls['put']) == 1
		assert len(TestAerospikeCache.client.calls['increment']) == 2
		assert len(TestAerospikeCache.client.calls['get']) == 1
