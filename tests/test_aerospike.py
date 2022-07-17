from kh_common.caching import key_value_store
from kh_common.logging import LogHandler; LogHandler.logging_available = False
from kh_common.caching.key_value_store import KeyValueStore
from tests.utilities.aerospike import AerospikeClient
from tests.utilities.caching import CachingTestClass
from kh_common.caching.integer import Integer
from kh_common.caching import AerospikeCache
import pytest
import time


client = AerospikeClient()
key_value_store._client = client
AerospikeCache.client = client


class TestAerospikeCache(CachingTestClass) :

	it = 0

	# def test_FormatCache_int(self) :
	# 	# setup
	# 	TestAerospikeCache.it = 0

	# 	@AerospikeCache('kheina', 'test', '{t}', local_TTL=5)
	# 	def cache_test(t) :
	# 		TestAerospikeCache.it += 1
	# 		return t + TestAerospikeCache.it - 1

	# 	# assert
	# 	# set
	# 	assert 1 == cache_test(1)
	# 	assert 3 == cache_test(2)
	# 	assert 5 == cache_test(3)

	# 	# local cache
	# 	assert 1 == cache_test(1)
	# 	assert 3 == cache_test(2)
	# 	assert 5 == cache_test(3)

	# 	# aerospike cache

	# 	# purge
	# 	assert 4 == cache_test(1)
	# 	assert 6 == cache_test(2)
	# 	assert 8 == cache_test(3)


	# def test_FormatCache_string(self) :
	# 	# setup
	# 	TestAerospikeCache.it = 0
	# 	kwargs = { 'a': 1, 'b': '2', 'c': 3.1 }

	# 	@AerospikeCache('kheina', 'test', '{t}.{a}', local_TTL=5)
	# 	def cache_test(t, **kv) :
	# 		TestAerospikeCache.it += 1
	# 		return f'{int(t) + TestAerospikeCache.it - 1}'

	# 	# assert
	# 	assert '1' == cache_test('1', **kwargs)
	# 	assert '3' == cache_test('2', **kwargs)
	# 	assert '5' == cache_test('3', **kwargs)

	# 	assert '1' == cache_test('1', **kwargs)
	# 	assert '3' == cache_test('2', **kwargs)
	# 	assert '5' == cache_test('3', **kwargs)

	# 	assert '4' == cache_test('1', **kwargs)
	# 	assert '6' == cache_test('2', **kwargs)
	# 	assert '8' == cache_test('3', **kwargs)


	# def test_FormatCache_FormatStringAllArgs(self) :
	# 	# setup
	# 	TestAerospikeCache.it = 0
	# 	default = 1

	# 	@AerospikeCache('kheina', 'test', '{t}.{a}', local_TTL=10)
	# 	def cache_test(t, a=default) :
	# 		TestAerospikeCache.it += 1
	# 		return TestAerospikeCache.it

	# 	# assert
	# 	assert 1 == cache_test(1)
	# 	assert 1 == cache_test(1, default)
	# 	assert 1 == cache_test(1, a=default)

	# 	assert 2 == cache_test(2)
	# 	assert 2 == cache_test(2, default)
	# 	assert 2 == cache_test(2, a=default)


	# def test_FormatCache_FormatStringSomeArgs(self) :
	# 	# setup
	# 	TestAerospikeCache.it = 0
	# 	default = 1

	# 	@AerospikeCache('kheina', 'test', '{a}', local_TTL=10)
	# 	def cache_test(t, a=default) :
	# 		TestAerospikeCache.it += 1
	# 		return TestAerospikeCache.it

	# 	# assert
	# 	assert 1 == cache_test(1)
	# 	assert 1 == cache_test(2)

	# 	assert 2 == cache_test(1, a=default + 1)
	# 	assert 2 == cache_test(2, a=default + 1)

	# 	assert 3 == cache_test(1, a=default + 2)
	# 	assert 3 == cache_test(2, a=default + 2)


@pytest.mark.asyncio
class TestAerospikeCacheAsync :
	pass


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
