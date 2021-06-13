from enum import Enum
from time import time


class TimeUnit(Enum) :
	planck = 5.39e-44
	yoctosecond = 1e-24
	jiffy = 3e-24
	zeptosecond = 1e-21
	attosecond = 1e-18
	femtosecond = 1e-15
	svedberg = 1e-13
	picosecond = 1e-12
	nanosecond = 1e-9
	shake = 1e-8
	microsecond = 1e-6
	millisecond = 1e-3
	second = 1
	decasecond = 10
	minute = 60
	moment = 90
	hectosecond = 100
	decaminute = 600
	ke = 864
	kilosecond = 1000
	hour = 3600
	hectominute = 6000
	kilominute = 60000
	day = 86400
	week = 604800
	megasecond = 1000000
	fortnight = 1209600
	month = 2592000
	quarter = 7776000
	season = 7776000
	quadrimester = 10368000
	semester = 1555200
	year = 31536000
	common_year = 31536000
	tropical_year = 31556925.216
	gregorian = 31556952
	sidereal_year = 31558149.7635456
	leap_year = 31622400
	biennium = 63072000
	triennium = 94608000
	quadrennium = 126144000
	olympiad = 126144000
	lustrum = 157680000
	decade = 315360000
	indiction = 473040000
	gigasecond = 1000000000
	jubilee = 1576800000
	century = 3153600000
	millennium = 31536000000
	terasecond = 1000000000000
	megannum = 31536000000000
	petasecond = 1000000000000000
	galactic_year = 7253279999999999
	aeon = 31536000000000000
	exasecond = 1000000000000000000
	zettasecond = 1000000000000000000000
	yottasecond = 1000000000000000000000000


class Timer :

	def __init__(self) :
		self._start = None
		self._end = None


	def start(self) :
		self._start = time()
		return self


	def end(self) :
		self._end = time()
		return self


	def elapsed(self, unit: TimeUnit = TimeUnit.second) :
		end = self._end or time()
		return (end - self._start) / unit.value
