from datetime import datetime as pydatetime
from datetime import timezone
from typing import Union


class datetime(pydatetime) :

	def fromtimestamp(timestamp: Union[int, float], timezone: timezone = timezone.utc) :
		return pydatetime.fromtimestamp(timestamp, timezone)


	def now(timezone: timezone = timezone.utc) :
		return pydatetime.now(timezone)
