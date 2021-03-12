from psycopg2.extensions import connection as Connection, cursor as Cursor
from psycopg2.errors import UniqueViolation, ConnectionException
from kh_common.utilities import getFullyQualifiedClassName
from typing import Any, Callable, Dict, List, Tuple, Union
from kh_common.config.repo import name, short_hash
from psycopg2 import Binary, connect as dbConnect
from kh_common.logging import getLogger, Logger
from kh_common.config.credentials import db
from traceback import format_tb
from types import TracebackType
from sys import exc_info


class SqlInterface :

	def __init__(self, conversions:Dict[type, Callable]={ }) -> type(None) :
		self.logger: Logger = getLogger()
		self._sql_connect()
		self._conversions: Dict[type, Callable] = {
			tuple: list,
			bytes: Binary,
			**conversions,
		}


	def _sql_connect(self) -> type(None) :
		try :
			self._conn: Connection = dbConnect(**db)

		except Exception as e :
			self.logger.critical(f'failed to connect to database!', exc_info=e)

		else :
			self.logger.info('connected to database.')


	def _convert_item(self, item: Any) -> Any :
		item_type = type(item)
		if item_type in self._conversions :
			return self._conversions[item_type](item)
		return item


	def query(self, sql: str, params:Tuple[Any]=(), commit:bool=False, fetch_one:bool=False, fetch_all:bool=False, maxretry:int=2) -> Union[type(None), List[Any]] :
		if self._conn.closed :
			self._sql_connect()

		params = tuple(map(self._convert_item, params))
		try :
			cur: Cursor = self._conn.cursor()
			cur.execute(sql, params)

			if commit :
				self._conn.commit()
			else :
				self._conn.rollback()

			if fetch_one :
				return cur.fetchone()
			elif fetch_all :
				return cur.fetchall()

		except ConnectionException as e :
			if maxretry > 1 :
				self.logger.warning('connection to db was severed, attempting to reconnect.', exc_info=e)
				self._sql_connect()
				return self.query(sql, params, commit, fetch_one, fetch_all, maxretry - 1)

			else :
				self.logger.critical('failed to reconnect to db.', exc_info=e)
				raise

		except Exception as e :
			self.logger.warning({
				'message': 'unexpected error encountered during sql query.',
				'query': sql,
			}, exc_info=e)
			# now attempt to recover by rolling back
			self._conn.rollback()
			raise

		finally :
			cur.close()


	def transaction(self) :
		return Transaction(self)


	def close(self) -> int :
		self._conn.close()
		return self._conn.closed


class Transaction :

	def __init__(self, sql: SqlInterface) :
		self._sql: SqlInterface = sql
		self.cur: Union[Cursor, type(None)] = None


	def __enter__(self) :
		for _ in range(2) :
			try :
				self.cur: Cursor = self._sql._conn.cursor()
				return self

			except ConnectionException as e :
				self._sql.logger.warning('connection to db was severed, attempting to reconnect.', exc_info=e)
				self._sql._sql_connect()

		raise ConnectionException('failed to reconnect to db.')


	def __exit__(self, exc_type, exc_obj, exc_tb) :
		if exc_type :
			self.rollback()
		self.cur.close()


	def commit(self) :
		self._sql._conn.commit()


	def rollback(self) :
		self._sql._conn.rollback()


	def query(self, sql: str, params:Tuple[Any]=(), fetch_one:bool=False, fetch_all:bool=False) -> Union[type(None), List[Any]] :
		params = tuple(map(self._sql._convert_item, params))
		try :
			self.cur.execute(sql, params)

			if fetch_one :
				return self.cur.fetchone()

			elif fetch_all :
				return self.cur.fetchall()

		except Exception as e :
			self._sql.logger.warning({
				'message': 'unexpected error encountered during sql query.',
				'query': sql,
			}, exc_info=e)
			raise
