from typing import Any, Dict, NamedTuple, Set
from pydantic import BaseModel
from datetime import datetime
from enum import Enum, unique
from uuid import UUID


class AuthToken(NamedTuple) :
	user_id: int
	expires: datetime
	guid: UUID
	data: Dict[str, Any]
	token_string: str


@unique
class Scope(Enum) :
	default: int = 0
	bot: int = 1
	user: int = 2
	mod: int = 3
	admin: int = 4
	internal: int = 5

	def all_included_scopes(self) :
		return [v for v in Scope.__members__.values() if Scope.user.value <= v.value <= self.value] or [self]


class KhUser(NamedTuple) :
	user_id: int
	token: AuthToken
	scope: Set[Scope]

	def __hash__(self) :
		return hash(f'{self.user_id}{self.scope}')


class PublicKeyResponse(BaseModel) :
	algorithm: str
	key: str
	signature: str
	issued: int
	expires: int
