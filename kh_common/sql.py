from psycopg2.errors import UniqueViolation, ConnectionException
from psycopg2 import Binary, connect as dbConnect
from kh_common import getFullyQualifiedClassName
from kh_common.config.credentials import db
from kh_common.logging import getLogger
from sys import exc_info


class SqlInterface :

	def __init__(self) :
		self.logger = getLogger('sql-interface')
		self._sql_connect()


	def _sql_connect(self) :
		try :
			self._conn = dbConnect(**db)

		except Exception as e :
			self.logger.critical({
				'message': f'failed to connect to database!',
				'error': f'{getFullyQualifiedClassName(e)}: {e}',
			})

		else :
			self.logger.info(f'connected to database.')


	def query(self, sql, params=(), commit=False, fetch_one=False, fetch_all=False, maxretry=2) :
		try :
			cur = self._conn.cursor()
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
				e, exc_tb = exc_info()[1:]
				self.logger.warning({
					'message': f'{getFullyQualifiedClassName(e)}: {e}',
					'stacktrace': format_tb(exc_tb),
				})
				return self.query(sql, params, commit, fetch_one, fetch_all, maxretry - 1)
			else :
				self.logger.exception({ })
				raise

		except :
			e, exc_tb = exc_info()[1:]
			self.logger.warning({
				'message': f'{getFullyQualifiedClassName(e)}: {e}',
				'stacktrace': format_tb(exc_tb),
			})
			# now attempt to recover by rolling back
			self._conn.rollback()
			raise

		finally :
			cur.close()


	def close(self) :
		self._conn.close()
		return self._conn.closed
