from kh_common.exceptions import GenericErrorHandler
from kh_common.caching import ArgsCache
from kh_common.sql import SqlInterface
from kh_common.hashing import Hashable
from typing import Set


class UserBlocking(SqlInterface, Hashable) :

	def __init__(self) :
		Hashable.__init__(self)
		SqlInterface.__init__(self)


	@GenericErrorHandler('fetching user blocked tags')
	@ArgsCache(60)
	def userBlockedTags(self, user_id: int) -> Set[str] :
		data = self.query(
			"""
			SELECT tags.tag
			FROM kheina.public.tag_blocking
				INNER JOIN kheina.public.tags
					ON tags.tag_id = blocked
						AND tags.deprecated = false
			WHERE user_id = %s;
			""",
			(user_id,)
			fetch_all=True,
		)

		return set(data)


	@GenericErrorHandler('fetching blocked users')
	@ArgsCache(60)
	def userBlockedUsers(self, user_id: int) -> Set[str] :
		data = self.query(
			"""
			SELECT users.handle
			FROM kheina.public.user_blocking
				INNER JOIN kheina.public.users
					ON users.user_id = blocked
			WHERE user_id = %s;
			""",
			(user_id,)
			fetch_all=True,
		)

		return set(data)
