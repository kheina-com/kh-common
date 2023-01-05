import pytest

from kh_common.caching import Aggregate, Aggregator, ArgsCache, KwargsCache, SimpleCache
from tests.utilities.caching import CachingTestClass


class TestSimpleCache(CachingTestClass) :

	def test_SimpleCache_int(self) :
		# arrange
		@SimpleCache(1)
		def simplecache_test(a) :
			return a

		# assert
		assert 1 == simplecache_test(1)
		assert 1 == simplecache_test(2)
		assert 3 == simplecache_test(3)


	def test_SimpleCache_string(self) :
		# arrange
		@SimpleCache(1)
		def simplecache_test(a) :
			return a

		# assert
		assert '1' == simplecache_test('1')
		assert '1' == simplecache_test('2')
		assert '3' == simplecache_test('3')


	def test_SimpleCache_mixed(self) :
		# arrange
		@SimpleCache(1)
		def simplecache_test(*a) :
			return a

		data = (1, '2', 3.1, (1, 2), { 'a': 1 }, [1, 2, 3])
		# assert
		assert data == simplecache_test(*data)
		assert data == simplecache_test(2)
		assert (3,) == simplecache_test(3)


class TestArgsCache(CachingTestClass) :

	it = 0

	def test_ArgsCache_int(self) :
		# arrange
		TestArgsCache.it = 0

		@ArgsCache(5)
		def argscache_test(a) :
			TestArgsCache.it += 1
			return a + TestArgsCache.it - 1

		# assert
		assert 1 == argscache_test(1)
		assert 3 == argscache_test(2)
		assert 5 == argscache_test(3)

		assert 1 == argscache_test(1)
		assert 3 == argscache_test(2)
		assert 5 == argscache_test(3)

		assert 4 == argscache_test(1)
		assert 6 == argscache_test(2)
		assert 8 == argscache_test(3)


	def test_ArgsCache_string(self) :
		# arrange
		TestArgsCache.it = 0

		@ArgsCache(5)
		def argscache_test(a) :
			TestArgsCache.it += 1
			return f'{int(a) + TestArgsCache.it - 1}'

		# assert
		assert '1' == argscache_test('1')
		assert '3' == argscache_test('2')
		assert '5' == argscache_test('3')

		assert '1' == argscache_test('1')
		assert '3' == argscache_test('2')
		assert '5' == argscache_test('3')

		assert '4' == argscache_test('1')
		assert '6' == argscache_test('2')
		assert '8' == argscache_test('3')


	def test_ArgsCache_mixed(self) :
		# arrange
		TestArgsCache.it = 0
		data = (1, '2', 3.1, (1, 2), { 'a': 1 }, [1, 2, 3])

		@ArgsCache(3)
		def argscache_test(*a) :
			TestArgsCache.it += 1
			return int(a[0]) + TestArgsCache.it - 1

		# assert
		with pytest.raises(TypeError) :
			argscache_test(*data)


@pytest.mark.asyncio
class TestArgsCacheAsync(CachingTestClass) :

	it = 0

	async def test_ArgsCache_int(self) :
		# arrange
		TestArgsCacheAsync.it = 0

		@ArgsCache(5)
		async def argscache_test(a) :
			TestArgsCacheAsync.it += 1
			return a + TestArgsCacheAsync.it - 1

		# assert
		assert 1 == await argscache_test(1)
		assert 3 == await argscache_test(2)
		assert 5 == await argscache_test(3)

		assert 1 == await argscache_test(1)
		assert 3 == await argscache_test(2)
		assert 5 == await argscache_test(3)

		assert 4 == await argscache_test(1)
		assert 6 == await argscache_test(2)
		assert 8 == await argscache_test(3)


	async def test_ArgsCache_string(self) :
		# arrange
		TestArgsCacheAsync.it = 0

		@ArgsCache(5)
		async def argscache_test(a) :
			TestArgsCacheAsync.it += 1
			return f'{int(a) + TestArgsCacheAsync.it - 1}'

		# assert
		assert '1' == await argscache_test('1')
		assert '3' == await argscache_test('2')
		assert '5' == await argscache_test('3')

		assert '1' == await argscache_test('1')
		assert '3' == await argscache_test('2')
		assert '5' == await argscache_test('3')

		assert '4' == await argscache_test('1')
		assert '6' == await argscache_test('2')
		assert '8' == await argscache_test('3')


	async def test_ArgsCache_mixed(self) :
		# arrange
		TestArgsCacheAsync.it = 0
		data = (1, '2', 3.1, (1, 2), { 'a': 1 }, [1, 2, 3])

		@ArgsCache(3)
		async def argscache_test(*a) :
			TestArgsCacheAsync.it += 1
			return int(a[0]) + TestArgsCacheAsync.it - 1

		# assert
		with pytest.raises(TypeError) :
			await argscache_test(*data)


class TestKwargsCache(CachingTestClass) :

	it = 0

	def test_KwargsCache_int(self) :
		# setup
		TestKwargsCache.it = 0
		kwargs = { 'a': 1, 'b': '2', 'c': 3.1 }

		@KwargsCache(5)
		def kwargscache_test(t, **kv) :
			TestKwargsCache.it += 1
			return t + TestKwargsCache.it - 1

		# assert
		assert 1 == kwargscache_test(1, **kwargs)
		assert 3 == kwargscache_test(2, **kwargs)
		assert 5 == kwargscache_test(3, **kwargs)

		assert 1 == kwargscache_test(1, **kwargs)
		assert 3 == kwargscache_test(2, **kwargs)
		assert 5 == kwargscache_test(3, **kwargs)

		assert 4 == kwargscache_test(1, **kwargs)
		assert 6 == kwargscache_test(2, **kwargs)
		assert 8 == kwargscache_test(3, **kwargs)


	def test_KwargsCache_string(self) :
		# setup
		TestKwargsCache.it = 0
		kwargs = { 'a': 1, 'b': '2', 'c': 3.1 }

		@KwargsCache(5)
		def kwargscache_test(t, **kv) :
			TestKwargsCache.it += 1
			return f'{int(t) + TestKwargsCache.it - 1}'

		# assert
		assert '1' == kwargscache_test('1', **kwargs)
		assert '3' == kwargscache_test('2', **kwargs)
		assert '5' == kwargscache_test('3', **kwargs)

		assert '1' == kwargscache_test('1', **kwargs)
		assert '3' == kwargscache_test('2', **kwargs)
		assert '5' == kwargscache_test('3', **kwargs)

		assert '4' == kwargscache_test('1', **kwargs)
		assert '6' == kwargscache_test('2', **kwargs)
		assert '8' == kwargscache_test('3', **kwargs)


	def test_KwargsCache_mixed(self) :
		# setup
		TestKwargsCache.it = 0
		data = (1, '2', 3.1, (1, 2), { 'a': 1 }, [1, 2, 3])
		kwargs1 = { 'a': 1, 'b': '2', 'c': 3.1 }
		kwargs2 = { 'a': 2, 'b': '2', 'c': 3.1 }

		@KwargsCache(3)
		def kwargscache_test(*a, **kv) :
			TestKwargsCache.it += 1
			return int(a[0]) + TestKwargsCache.it - 1

		# assert
		assert 1 == kwargscache_test(*data, **kwargs1)
		assert 2 == kwargscache_test(*data, **kwargs2)

		assert 1 == kwargscache_test(*data, **kwargs1)
		assert 2 == kwargscache_test(*data, **kwargs2)

		assert 3 == kwargscache_test(*data, **kwargs1)
		assert 4 == kwargscache_test(*data, **kwargs2)


	def test_KwargsCache_default(self) :
		# setup
		TestKwargsCache.it = 0
		default = 1

		@KwargsCache(10)
		def kwargscache_test(a, b=default) :
			TestKwargsCache.it += 1
			return TestKwargsCache.it

		# assert
		assert 1 == kwargscache_test(1)
		assert 1 == kwargscache_test(1, default)
		assert 1 == kwargscache_test(1, b=default)


@pytest.mark.asyncio
class TestKwargsCacheAsync(CachingTestClass) :

	it = 0

	async def test_KwargsCache_int(self) :
		# setup
		TestKwargsCacheAsync.it = 0
		kwargs = { 'a': 1, 'b': '2', 'c': 3.1 }

		@KwargsCache(5)
		async def kwargscache_test(t, **kv) :
			TestKwargsCacheAsync.it += 1
			return t + TestKwargsCacheAsync.it - 1

		# assert
		assert 1 == await kwargscache_test(1, **kwargs)
		assert 3 == await kwargscache_test(2, **kwargs)
		assert 5 == await kwargscache_test(3, **kwargs)

		assert 1 == await kwargscache_test(1, **kwargs)
		assert 3 == await kwargscache_test(2, **kwargs)
		assert 5 == await kwargscache_test(3, **kwargs)

		assert 4 == await kwargscache_test(1, **kwargs)
		assert 6 == await kwargscache_test(2, **kwargs)
		assert 8 == await kwargscache_test(3, **kwargs)


	async def test_KwargsCache_string(self) :
		# setup
		TestKwargsCacheAsync.it = 0
		kwargs = { 'a': 1, 'b': '2', 'c': 3.1 }

		@KwargsCache(5)
		async def kwargscache_test(t, **kv) :
			TestKwargsCacheAsync.it += 1
			return f'{int(t) + TestKwargsCacheAsync.it - 1}'

		# assert
		assert '1' == await kwargscache_test('1', **kwargs)
		assert '3' == await kwargscache_test('2', **kwargs)
		assert '5' == await kwargscache_test('3', **kwargs)

		assert '1' == await kwargscache_test('1', **kwargs)
		assert '3' == await kwargscache_test('2', **kwargs)
		assert '5' == await kwargscache_test('3', **kwargs)

		assert '4' == await kwargscache_test('1', **kwargs)
		assert '6' == await kwargscache_test('2', **kwargs)
		assert '8' == await kwargscache_test('3', **kwargs)


	async def test_KwargsCache_mixed(self) :
		# setup
		TestKwargsCacheAsync.it = 0
		data = (1, '2', 3.1, (1, 2), { 'a': 1 }, [1, 2, 3])
		kwargs1 = { 'a': 1, 'b': '2', 'c': 3.1 }
		kwargs2 = { 'a': 2, 'b': '2', 'c': 3.1 }

		@KwargsCache(3)
		async def kwargscache_test(*a, **kv) :
			TestKwargsCacheAsync.it += 1
			return int(a[0]) + TestKwargsCacheAsync.it - 1

		# assert
		assert 1 == await kwargscache_test(*data, **kwargs1)
		assert 2 == await kwargscache_test(*data, **kwargs2)

		assert 1 == await kwargscache_test(*data, **kwargs1)
		assert 2 == await kwargscache_test(*data, **kwargs2)

		assert 3 == await kwargscache_test(*data, **kwargs1)
		assert 4 == await kwargscache_test(*data, **kwargs2)


	async def test_KwargsCache_default(self) :
		# setup
		TestKwargsCacheAsync.it = 0
		default = 1

		@KwargsCache(10)
		async def kwargscache_test(a, b=default) :
			TestKwargsCacheAsync.it += 1
			return TestKwargsCacheAsync.it

		# assert
		assert 1 == await kwargscache_test(1)
		assert 1 == await kwargscache_test(1, default)
		assert 1 == await kwargscache_test(1, b=default)


class TestAggregate(CachingTestClass) :

	def test_Aggregate_Sum(self) :
		# setup
		count = 100
		data1 = list(range(count))
		data2 = list(range(count, count * 2))

		@Aggregate(count - 1, aggregator=Aggregator.Sum)
		def aggregate_test(a, b=None) :
			return a, b

		# act
		for i in range(count) :
			result = aggregate_test(data1[i], data2[i])

		# assert
		assert sum(data1) == result[0]
		assert sum(data2) == result[1]


	def test_Aggregate_Average(self) :
		# setup
		count = 100
		data1 = list(range(count))
		data2 = list(range(count, count * 2))

		@Aggregate(count - 1, aggregator=Aggregator.Average)
		def aggregate_test(a, b=None) :
			return a, b

		# act
		for i in range(count) :
			result = aggregate_test(data1[i], data2[i])

		# assert
		assert sum(data1) / count == result[0]
		assert sum(data2) / count == result[1]


	def test_Aggregate_StandardDeviation(self) :
		# setup
		data = [727.7, 1086.5, 1091.0, 1361.3, 1490.5, 1956.1]
		expected = 420.962489619522557404707185924053192138671875

		@Aggregate(len(data) - 1, aggregator=Aggregator.StandardDeviation)
		def aggregate_test(a, b=None) :
			return a, b

		# act
		for i in data :
			result = aggregate_test(i, i)

		# assert
		assert format(expected, '.12g') == format(result[0].deviation, '.12g')
		assert len(data) == result[0].count
		assert sum(data) / len(data) == result[0].average
		assert format(expected, '.12g') == format(result[1].deviation, '.12g')
