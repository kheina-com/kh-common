from datetime import datetime
from enum import Enum, IntEnum, unique
from typing import Any, Dict, List, NamedTuple, Optional, Set, Type, Union
from uuid import UUID

from pydantic import BaseModel, conbytes


# from avrofastapi.models import RefId
# from avrofastapi.schema import AvroException, AvroSchemaGenerator, _validate_avro_name, _validate_avro_namespace, get_name


class AuthToken(NamedTuple) :
	user_id: int
	expires: datetime
	guid: UUID
	data: Dict[str, Any]
	token_string: str


@unique
class Scope(IntEnum) :
	default: int = 0
	bot: int = 1
	user: int = 2
	mod: int = 3
	admin: int = 4
	internal: int = 5

	def all_included_scopes(self) -> List['Scope'] :
		return [v for v in Scope.__members__.values() if Scope.user.value <= v.value <= self.value] or [self]


class KhUser(NamedTuple) :
	user_id: int
	token: AuthToken
	scope: Set[Scope]

	def __hash__(self) -> int :
		return hash(f'{self.user_id}{self.scope}')


	def __str__(self) -> str :
		# this is here for caching purposes
		return str(self.user_id)


class PublicKeyResponse(BaseModel) :
	algorithm: str
	key: str
	signature: str
	issued: datetime
	expires: datetime


@unique
class AuthState(IntEnum) :
	active: int = 0
	inactive: int = 1


class TokenMetadata(BaseModel) :
	state: AuthState
	key_id: int
	user_id: int
	version: bytes
	algorithm: str
	expires: datetime
	issued: datetime
	fingerprint: bytes


@unique
class AuthAlgorithm(Enum) :
	ed25519: str = 'ed25519'


class TokenResponse(BaseModel) :
	version: str
	algorithm: AuthAlgorithm
	key_id: int
	issued: datetime
	expires: datetime
	token: str


class LoginResponse(BaseModel) :
	user_id: int
	handle: str
	name: Optional[str]
	mod: bool
	token: TokenResponse


# class TokenV2Payload(BaseModel) :
# 	algorithm: AuthAlgorithm
# 	key_id: int
# 	user_id: int
# 	expires: datetime
# 	guid: RefId
# 	scope: Set[Scope]
# 	fingerprint: conbytes(min_length=40, max_length=40)
# 	ip: bytes


# class SetEnabledAvroSchemaGenerator(AvroSchemaGenerator) :

# 	def __init__(self, *args, **kwargs) :
# 		super().__init__(*args, **kwargs, conversions={
# 			set: AvroSchemaGenerator._convert_array,
# 			IntEnum: SetEnabledAvroSchemaGenerator._convert_int_enum,
# 		})


# 	def _convert_int_enum(self: 'AvroSchemaGenerator', model: Type[IntEnum]) -> Dict[str, Union[str, List[str]]] :
# 		name: str = get_name(model)
# 		_validate_avro_name(name)

# 		values: Optional[List[str]] = list(map(lambda x : x.name, model.__members__.values()))

# 		if len(values) != len(set(values)) :
# 			raise AvroException('enums must contain all unique names to be avro encoded')

# 		schema: Dict[str, Union[str, List[str]]] = {
# 			'type': 'enum',
# 			'name': name,
# 			'symbols': values,
# 		}

# 		self_namespace: Optional[str] = getattr(model, '__namespace__', None)
# 		if self_namespace :
# 			_validate_avro_namespace(self_namespace, self.namespace)
# 			schema['namespace'] = self_namespace

# 		return schema
