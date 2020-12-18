from kh_common.caching import SimpleCache, ArgsCache, KwargsCache, Aggregate, Aggregator
from kh_common import caching


# global setup
caching.fake_time_store = 1
def fake_time() :
	caching.fake_time_store += 1
	return caching.fake_time_store - 1

caching.time = fake_time


class TestSimpleCache :

	def test_simplecache_int(self) :
		# setup
		@SimpleCache(1)
		def simplecache_test(a) :
			return a

		# assert
		assert 1 == simplecache_test(1)
		assert 1 == simplecache_test(2)
		assert 3 == simplecache_test(3)


	def test_simplecache_string(self) :
		# setup
		@SimpleCache(1)
		def simplecache_test(a) :
			return a

		# assert
		assert '1' == simplecache_test('1')
		assert '1' == simplecache_test('2')
		assert '3' == simplecache_test('3')


	def test_simplecache_mixed(self) :
		# setup
		@SimpleCache(1)
		def simplecache_test(*a) :
			return a

		data = (1, '2', 3.1, (1, 2), { 'a': 1 }, [1, 2, 3])
		# assert
		assert data == simplecache_test(*data)
		assert data == simplecache_test(2)
		assert (3,) == simplecache_test(3)


class TestArgsCache :

	it = 0

	def test_argscache_int(self) :
		# setup
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


	def test_argscache_string(self) :
		# setup
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


	def test_argscache_mixed(self) :
		# setup
		TestArgsCache.it = 0
		data1 = (1, '2', 3.1, (1, 2), { 'a': 1 }, [1, 2, 3])
		data2 = (5, '2', 3.1, (1, 2), { 'a': 2 }, [1, 2, 3])

		@ArgsCache(3)
		def argscache_test(*a) :
			TestArgsCache.it += 1
			return int(a[0]) + TestArgsCache.it - 1

		# assert
		assert 1 == argscache_test(*data1)
		assert 6 == argscache_test(*data2)

		assert 1 == argscache_test(*data1)
		assert 6 == argscache_test(*data2)

		assert 3 == argscache_test(*data1)
		assert 8 == argscache_test(*data2)

class TestKwargsCache :

	it = 0

	def test_kwargscache_int(self) :
		# setup
		TestArgsCache.it = 0
		kwargs = { 'a': 1, 'b': '2', 'c': 3.1 }

		@KwargsCache(5)
		def kwargscache_test(t, **kv) :
			TestArgsCache.it += 1
			return t + TestArgsCache.it - 1

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


	def test_kwargscache_string(self) :
		# setup
		TestArgsCache.it = 0
		kwargs = { 'a': 1, 'b': '2', 'c': 3.1 }

		@KwargsCache(5)
		def kwargscache_test(t, **kv) :
			TestArgsCache.it += 1
			return f'{int(t) + TestArgsCache.it - 1}'

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


	def test_kwargscache_mixed(self) :
		# setup
		TestArgsCache.it = 0
		data = (1, '2', 3.1, (1, 2), { 'a': 1 }, [1, 2, 3])
		kwargs1 = { 'a': 1, 'b': '2', 'c': 3.1 }
		kwargs2 = { 'a': 2, 'b': '2', 'c': 3.1 }

		@KwargsCache(3)
		def kwargscache_test(*a, **kv) :
			TestArgsCache.it += 1
			return int(a[0]) + TestArgsCache.it - 1

		# assert
		assert 1 == kwargscache_test(*data, **kwargs1)
		assert 2 == kwargscache_test(*data, **kwargs2)

		assert 1 == kwargscache_test(*data, **kwargs1)
		assert 2 == kwargscache_test(*data, **kwargs2)

		assert 3 == kwargscache_test(*data, **kwargs1)
		assert 4 == kwargscache_test(*data, **kwargs2)


class TestAggregate :

	def test_aggregate_sum(self) :
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


	def test_aggregate_average(self) :
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


	def test_aggregate_standarddeviation(self) :
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
		assert expected == result[0].deviation
		assert len(data) == result[0].count
		assert sum(data) / len(data) == result[0].average
		assert expected == result[1].deviation

