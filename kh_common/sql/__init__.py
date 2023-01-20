from asyncio import get_event_loop
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from types import TracebackType
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

from psycopg2 import Binary
from psycopg2 import connect as dbConnect
from psycopg2.errors import ConnectionException
from psycopg2.extensions import connection as Connection
from psycopg2.extensions import cursor as Cursor

from kh_common.config.credentials import db
from kh_common.logging import Logger, getLogger
from kh_common.sql.query import Query
from kh_common.timing import Timer


class SqlInterface :

	_conn: Connection = None

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
			SqlInterface._conn: Connection = dbConnect(**db)

		except Exception as e :
			self.logger.critical(f'failed to connect to database!', exc_info=e)

		else :
			self.logger.info('connected to database.')


	def _convert_item(self: 'SqlInterface', item: Any) -> Any :
		for cls in type(item).__mro__ :
			if cls in self._conversions :
				return self._conversions[cls](item)
		return item


	def query(self: 'SqlInterface', sql: Union[str, Query], params:Tuple[Any]=(), commit:bool=False, fetch_one:bool=False, fetch_all:bool=False, maxretry:int=2) -> Optional[List[Any]] :
		if SqlInterface._conn.closed :
			self._sql_connect()

		if isinstance(sql, Query) :
			sql, params = sql.build()

		params = tuple(map(self._convert_item, params))

		try :
			cur: Cursor = SqlInterface._conn.cursor()

			timer = Timer().start()

			cur.execute(sql, params)

			if commit :
				SqlInterface._conn.commit()

			else :
				SqlInterface._conn.rollback()

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
			SqlInterface._conn.rollback()
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
		SqlInterface._conn.close()
		return SqlInterface._conn.closed


class Transaction :

	def __init__(self: 'Transaction', sql: SqlInterface) :
		self._sql: SqlInterface = sql
		self.cur: Optional[Cursor] = None


	def __enter__(self: 'Transaction') :
		for _ in range(2) :
			try :
				self.cur: Cursor = SqlInterface._conn.cursor()
				return self

			except ConnectionException as e :
				self._sql.logger.warning('connection to db was severed, attempting to reconnect.', exc_info=e)
				self._sql._sql_connect()

		raise ConnectionException('failed to reconnect to db.')


	def __exit__(self: 'Transaction', exc_type: Optional[Type[BaseException]], exc_obj: Optional[BaseException], exc_tb: Optional[TracebackType]) :
		if exc_type :
			self.rollback()
		self.cur.close()


	def commit(self: 'Transaction') :
		SqlInterface._conn.commit()


	def rollback(self: 'Transaction') :
		SqlInterface._conn.rollback()


	def query(self: 'Transaction', sql: Union[str, Query], params:Tuple[Any]=(), fetch_one:bool=False, fetch_all:bool=False) -> Optional[List[Any]] :
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


	@wraps(query)
	async def query_async(self: 'Transaction', *args, **kwargs) :
		with ThreadPoolExecutor() as threadpool :
			return await get_event_loop().run_in_executor(threadpool, partial(self.query, *args, **kwargs))
