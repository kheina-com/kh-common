from pytz import all_timezones, common_timezones, timezone
from datetime import timezone, datetime as pydatetime
from typing import Union


timezones = { tz._utcoffset: tz for tz in map(timezone, all_timezones + common_timezones) if tz._utcoffset.total_seconds() % 3600 == 0 }


class datetime(pydatetime) :

	def fromtimestamp(timestamp: Union[int, float], timezone: timezone = timezone.utc) :
		return pydatetime.fromtimestamp(timestamp, timezone)


	def now(timezone: timezone = timezone.utc) :
		return pydatetime.now(timezone)


	def normalize(datetime: pydatetime) :
		return timezones[datetime.utcoffset()].normalize(datetime)
