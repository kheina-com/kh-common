from kh_common.logging import LogHandler; LogHandler.logging_available = False
from kh_common.caching.key_value_store import KeyValueStore
from tests.utilities.aerospike import AerospikeClient
from tests.utilities.caching import CachingTestClass
from kh_common.caching.integer import Integer
from kh_common.caching import AerospikeCache
import pytest
import time


client = AerospikeClient()
KeyValueStore._client = client
Integer._client = client


class TestAerospikeCache(CachingTestClass) :

	it = 0

	def test_FormatCache_int(self) :
		# setup
		client.clear()
		TestAerospikeCache.it = 0

		@AerospikeCache('kheina', 'test', '{t}.{a}', 0, local_TTL=5)
		def cache_test(t, a=2) :
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
		assert 3 == len(client.calls['put'])
		assert 6 == len(client.calls['get'])  # initial set runs get + aerospike retrieval

		# purge
		client.clear()

		# local cache again
		assert 1 == cache_test(1)
		assert 3 == cache_test(2)
		assert 5 == cache_test(3)

		# reset
		assert 4 == cache_test(1)
		assert 6 == cache_test(2)
		assert 8 == cache_test(3)

		assert 3 == len(client.calls['put'])
		assert 3 == len(client.calls['get'])


@pytest.mark.asyncio
class TestAerospikeCacheAsync(CachingTestClass) :

	it = 0

	async def test_async_FormatCache_int(self) :
		# setup
		client.clear()
		TestAerospikeCache.it = 0

		@AerospikeCache('kheina', 'test', '{t}.{a}', 0, local_TTL=5)
		async def cache_test(t, a=2, b=1) :
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
		assert 3 == len(client.calls['put'])
		assert 6 == len(client.calls['get'])  # initial set runs get + aerospike retrieval

		# purge
		client.clear()

		# local cache again
		assert 1 == await cache_test(1)
		assert 3 == await cache_test(2)
		assert 5 == await cache_test(3)

		# reset
		assert 4 == await cache_test(1)
		assert 6 == await cache_test(2)
		assert 8 == await cache_test(3)

		assert 3 == len(client.calls['put'])
		assert 3 == len(client.calls['get'])  # initial set runs get + aerospike retrieval


class TestKeyValueStore :

	def test_Get_LocalCacheEmpty_ClientReturnsValue(self) :

		# arrange
		key = 'key'
		data = 1

		client.clear()
		client.put(('kheina', 'test', key), { 'data': data })
		client.calls.clear()

		kvs = KeyValueStore('kheina', 'test')

		# apply
		result = kvs.get(key)

		# assert
		assert result == data
		assert len(client.calls['get']) == 1


	def test_Get_LocalCachePopulated_ClientNotCalled(self) :

		# arrange
		key = 'key'
		data = 1

		client.clear()
		client.put(('kheina', 'test', key), { 'data': data })
		client.calls.clear()

		kvs = KeyValueStore('kheina', 'test')

		# apply
		result = kvs.put(key, data)
		result = kvs.get(key)

		# assert
		assert result == data
		assert len(client.calls['get']) == 0


	def test_Get_LocalCacheCleaned_ClientReturnsValue(self) :

		# arrange
		key = 'key'
		data = 1

		client.clear()
		client.put(('kheina', 'test', key), { 'data': data })
		client.calls.clear()

		kvs = KeyValueStore('kheina', 'test')
		kvs._cache[key] = (time.time(), data)

		# apply
		result = kvs.get(key)

		# assert
		assert result == data
		assert len(client.calls['get']) == 1


	def test_Get_LocalTTLZero_LocalCacheNotUsed(self) :

		# arrange
		key = 'key'
		data = 1

		client.clear()
		client.put(('kheina', 'test', key), { 'data': data })
		client.calls.clear()

		kvs = KeyValueStore('kheina', 'test', local_TTL=0)

		# apply
		result = kvs.get(key)
		result = kvs.get(key)

		# assert
		assert result == data
		assert len(client.calls['get']) == 2


	def test_Put_CacheEmpty_CacheCalledCorrectly(self) :

		# arrange
		key = 'key'
		data = 1

		client.clear()

		kvs = KeyValueStore('kheina', 'test', local_TTL=0)

		# apply
		kvs.put(key, data)
		result = kvs.get(key)

		# assert
		assert result == data
		assert len(client.calls['put']) == 1
		assert len(client.calls['get']) == 1
		assert client.calls['put'][0] == (('kheina', 'test', key), { 'data': data }, { 'ttl': 0 }, { 'max_retries': 3 })


	def test_Put_TTLSet_CacheCalledCorrectly(self) :

		# arrange
		key = 'key'
		data = 1

		client.clear()

		kvs = KeyValueStore('kheina', 'test', local_TTL=0)

		# apply
		kvs.put(key, data, TTL=1000)
		result = kvs.get(key)

		# assert
		assert result == data
		assert len(client.calls['put']) == 1
		assert len(client.calls['get']) == 1
		assert client.calls['put'][0] == (('kheina', 'test', key), { 'data': data }, { 'ttl': 1000 }, { 'max_retries': 3 })


	def test_Put_CachePopulated_CacheOverWritten(self) :

		# arrange
		key = 'key'
		different_data = 10
		data = 1

		client.clear()

		kvs = KeyValueStore('kheina', 'test', local_TTL=0)

		# apply
		kvs.put(key, data)
		kvs.put(key, different_data)
		result = kvs.get(key)

		# assert
		assert result == different_data
		assert len(client.calls['put']) == 2
		assert len(client.calls['get']) == 1
		assert client.calls['put'][-1] == (('kheina', 'test', key), { 'data': different_data }, { 'ttl': 0 }, { 'max_retries': 3 })


	def test_GetMany_HalfLocalHalfRemotePopulated_AllValuesReturned(self) :

		# arrange
		client.clear()
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
		assert len(client.calls['get']) == 0
		assert len(client.calls['get_many']) == 1
		# only the keys not held in local cache were called
		assert set(client.calls['get_many'][0]) == set(('kheina', 'test', key) for key in keys[:5])


	def test_GetMany_RemotePopulated_AllValuesReturned(self) :

		# arrange
		client.clear()
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
		assert len(client.calls['get']) == 0
		assert len(client.calls['get_many']) == 1
		# only the keys not held in local cache were called
		assert set(client.calls['get_many'][0]) == set(('kheina', 'test', key) for key in keys)


	def test_GetMany_LocalPopulated_AllValuesReturned(self) :

		# arrange
		client.clear()
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
		assert len(client.calls['get']) == 0
		assert len(client.calls['get_many']) == 0


class TestInteger :

	def test_set_CacheEmpty_LocalCachePopulated(self) :

		# arrange
		client.clear()

		data = 100

		i = Integer('kheina', 'test', 'an_int')

		# apply
		i.set(data)
		result = i.get()

		# assert
		assert result == data
		assert len(client.calls['put']) == 1
		assert len(client.calls['get']) == 0


	def test_set_CacheEmpty_AerospikeCachePopulated(self) :

		# arrange
		client.clear()

		data = 100

		i = Integer('kheina', 'test', 'an_int', local_TTL=0)

		# apply
		i.set(data)
		result = i.get()

		# assert
		assert result == data
		assert len(client.calls['put']) == 1
		assert len(client.calls['get']) == 1


	def test_increment_CachePopulated_CacheIncrement(self) :

		# arrange
		client.clear()

		data = 100

		i = Integer('kheina', 'test', 'an_int', local_TTL=0)

		# apply
		i.set(data)
		i.increment()
		result = i.get()

		# assert
		assert result == data + 1
		assert len(client.calls['put']) == 1
		assert len(client.calls['increment']) == 1
		assert len(client.calls['get']) == 1


	def test_increment_CachePopulated_CacheIncrementMany(self) :

		# arrange
		client.clear()

		data = 100

		i = Integer('kheina', 'test', 'an_int', local_TTL=0)

		# apply
		i.set(data)
		i.increment(11)
		i.increment(-7)
		result = i.get()

		# assert
		assert result == 104
		assert len(client.calls['put']) == 1
		assert len(client.calls['increment']) == 2
		assert len(client.calls['get']) == 1
