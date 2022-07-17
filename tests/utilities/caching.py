from kh_common import caching
import time


class CachingTestClass :

	def setup_method(self) :
		# global setup
		caching.fake_time_store = 1
		def fake_time() :
			caching.fake_time_store += 1
			return caching.fake_time_store - 1

		caching.time = fake_time


	def teardown_method(self) :
		caching.time = time.time
