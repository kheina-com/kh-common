from psycopg2.extensions import connection as Connection, cursor as Cursor
from psycopg2.errors import UniqueViolation, ConnectionException
from psycopg2 import Binary, connect as dbConnect
from kh_common import getFullyQualifiedClassName
from kh_common.logging import getLogger, Logger
from kh_common.config.credentials import db
from typing import Any, List, Tuple, Union
from traceback import format_tb
from types import TracebackType
from sys import exc_info



class SqlInterface :

	def __init__(self) -> type(None) :
		self.logger: Logger = getLogger('sql-interface')
		self._sql_connect()


	def _sql_connect(self) -> type(None) :
		try :
			self._conn: Connection = dbConnect(**db)

		except Exception as e :
			self.logger.critical({
				'message': f'failed to connect to database!',
				'error': f'{getFullyQualifiedClassName(e)}: {e}',
			})

		else :
			self.logger.info('connected to database.')


	def query(self, sql: str, params:Tuple[Any]=(), commit:bool=False, fetch_one:bool=False, fetch_all:bool=False, maxretry:int=2) -> Union[type(None), List[Any]] :
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

		except ConnectionException :
			self.connect()
			if maxretry > 1 :
				e: ConnectionException
				traceback: TracebackType
				e, traceback = exc_info()[1:]
				self.logger.warning({
					'message': f'{getFullyQualifiedClassName(e)}: {e}',
					'stacktrace': format_tb(traceback),
				})
				return self.query(sql, params, commit, fetch_one, fetch_all, maxretry - 1)
			else :
				self.logger.exception({ })
				raise

		except :
			e: Exception
			traceback: TracebackType
			e, traceback = exc_info()[1:]
			self.logger.warning({
				'message': f'{getFullyQualifiedClassName(e)}: {e}',
				'stacktrace': format_tb(traceback),
			})
			# now attempt to recover by rolling back
			self._conn.rollback()
			raise

		finally :
			cur.close()


	def close(self) -> int :
		self._conn.close()
		return self._conn.closed
