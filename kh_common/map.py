from kh_common.sql import SqlInterface
from typing import Any, Hashable


class Map(SqlInterface, dict) :

	def __init__(self, table: str, key: str, value: str) :
		assert table.startswith('kheina.public.')
		SqlInterface.__init__(self)
		self._table = table
		self._key = key
		self._value = value


	def __missing__(self, key: Hashable) -> Any:
		data: Any = self.query(f"""
			SELECT {self._value}
			FROM {self._table}
			WHERE {self._key} = %s
			LIMIT 1;
			""",
			(key,),
			fetch_one=True,
		)
		self[key] = data[0]
		return data[0]
