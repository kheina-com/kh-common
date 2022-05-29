from psycopg2.extensions import connection as Connection, cursor as Cursor
from typing import Any, Callable, Dict, List, Tuple, Union
from psycopg2 import Binary, connect as dbConnect
from concurrent.futures import ThreadPoolExecutor
from psycopg2.errors import ConnectionException
from kh_common.logging import getLogger, Logger
from kh_common.config.credentials import db
from kh_common.sql.query import Query
from functools import partial, wraps
from asyncio import get_event_loop
from kh_common.timing import Timer


class SqlInterface :

	def __init__(self: 'SqlInterface', long_query_metric: float = 1, conversions: Dict[type, Callable] = { }) -> None :
		self.logger: Logger = getLogger()
		self._sql_connect()
		self._long_query = long_query_metric
		self._conversions: Dict[type, Callable] = {
			tuple: list,
			bytes: Binary,
			**conversions,
		}


	def _sql_connect(self: 'SqlInterface') -> None :
		try :
			self._conn: Connection = dbConnect(**db)

		except Exception as e :
			self.logger.critical(f'failed to connect to database!', exc_info=e)

		else :
			self.logger.info('connected to database.')


	def _convert_item(self: 'SqlInterface', item: Any) -> Any :
		item_type = type(item)
		if item_type in self._conversions :
			return self._conversions[item_type](item)
		return item


	def query(self: 'SqlInterface', sql: Union[str, Query], params:Tuple[Any]=(), commit:bool=False, fetch_one:bool=False, fetch_all:bool=False, maxretry:int=2) -> Union[None, List[Any]] :
		if self._conn.closed :
			self._sql_connect()

		if isinstance(sql, Query) :
			sql, params = sql.build()

		params = tuple(map(self._convert_item, params))

		try :
			cur: Cursor = self._conn.cursor()

			timer = Timer().start()

			cur.execute(sql, params)

			if commit :
				self._conn.commit()

			else :
				self._conn.rollback()

			if timer.elapsed() > self._long_query :
				self.logger.warning(f'query took longer than {self._long_query} seconds:\n{sql}')

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


	@wraps(query)
	async def query_async(self: 'SqlInterface', *args, **kwargs) :
		with ThreadPoolExecutor() as threadpool :
			return await get_event_loop().run_in_executor(threadpool, partial(self.query, *args, **kwargs))


	def transaction(self: 'SqlInterface') -> 'Transaction' :
		return Transaction(self)


	def close(self: 'SqlInterface') -> int :
		self._conn.close()
		return self._conn.closed


class Transaction :

	def __init__(self, sql: SqlInterface) :
		self._sql: SqlInterface = sql
		self.cur: Union[Cursor, None] = None


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


	def query(self, sql: Union[str, Query], params:Tuple[Any]=(), fetch_one:bool=False, fetch_all:bool=False) -> Union[None, List[Any]] :
		if isinstance(sql, Query) :
			sql, params = sql.build()

		params = tuple(map(self._sql._convert_item, params))

		try :
			timer = Timer().start()

			self.cur.execute(sql, params)

			if timer.elapsed() > self._sql._long_query :
				self._sql.logger.warning(f'query took longer than {self._sql._long_query} seconds:\n{sql}')

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
