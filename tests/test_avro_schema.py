from datetime import date
from kh_common.logging import LogHandler; LogHandler.logging_available = False
from pydantic import BaseModel, conbytes, condecimal
from typing import Dict, List, Optional, Type, Union
from kh_common.models import Error, ValidationError
from kh_common.avro.schema import convert_schema
from kh_common.datetime import datetime
from avro.errors import AvroException
from datetime import date, time
from decimal import Decimal
from pytest import raises
from enum import Enum
import pytest


class BasicModelBaseTypes(BaseModel) :
	A: str
	B: int
	C: float
	D: bytes
	E: bool


class BasicEnum(Enum) :
	test1: str = 'TEST1'
	test2: str = 'TEST2'
	test3: str = 'TEST3'


class BasicModelAdvancedTypes(BaseModel) :
	A: datetime
	B: conbytes(max_length=10, min_length=10)
	C: condecimal(max_digits=5, decimal_places=3)
	D: BasicEnum
	E: date
	F: time


class NestedModelBasicTypes(BaseModel) :
	A: BasicModelBaseTypes
	B: int


class BasicModelTypingTypes(BaseModel) :
	A: List[int]
	B: Dict[str, int]
	C: Optional[int]
	D: Union[int, str]


class BasicModelCustomNamespace(BaseModel) :
	__namespace__: str = 'custom_namespace'
	A: int


class NestedModelCustomNamespace(BaseModel) :
	A: BasicModelCustomNamespace


@pytest.mark.parametrize(
	'input_model, expected', [
		(BasicModelBaseTypes, { 'namespace': 'BasicModelBaseTypes', 'name': 'BasicModelBaseTypes', 'type': 'record', 'fields': [{ 'name': 'A', 'type': 'string' }, { 'name': 'B', 'type': 'long' }, { 'name': 'C', 'type': 'double' }, { 'name': 'D', 'type': 'bytes' }, { 'name': 'E', 'type': 'boolean' }] }),
		(BasicModelAdvancedTypes, { 'namespace': 'BasicModelAdvancedTypes', 'name': 'BasicModelAdvancedTypes', 'type': 'record', 'fields': [{ 'name': 'A', 'type': { 'type': 'long', 'logicalType': 'timestamp-micros' } }, { 'name': 'B', 'type': { 'name': 'Bytes_10', 'type': 'fixed', 'size': 10 } }, { 'name': 'C', 'type': { 'type': 'bytes', 'logicalType': 'decimal', 'precision': 5, 'scale': 3 } }, { 'name': 'D', 'type': { 'name': 'BasicEnum', 'type': 'enum', 'symbols': ['TEST1', 'TEST2', 'TEST3'] } }, { 'name': 'E', 'type': { 'type': 'int', 'logicalType': 'date' } }, { 'name': 'F', 'type': { 'type': 'long', 'logicalType': 'time-micros' } }] }),
		(NestedModelBasicTypes, { 'namespace': 'NestedModelBasicTypes', 'name': 'NestedModelBasicTypes', 'type': 'record', 'fields': [{ 'name': 'A', 'type': { 'namespace': 'NestedModelBasicTypes', 'name': 'BasicModelBaseTypes', 'type': 'record', 'fields': [{ 'name': 'A', 'type': 'string' }, { 'name': 'B', 'type': 'long' }, { 'name': 'C', 'type': 'double' }, { 'name': 'D', 'type': 'bytes' }, { 'name': 'E', 'type': 'boolean' }] } }, { 'name': 'B', 'type': 'long' }] }),
		(BasicModelTypingTypes, { 'namespace': 'BasicModelTypingTypes', 'name': 'BasicModelTypingTypes', 'type': 'record', 'fields': [{ 'name': 'A', 'type': { 'type': 'array', 'namespace': 'BasicModelTypingTypes', 'items': 'long' } }, { 'name': 'B', 'type': { 'type': 'map', 'values': 'long' } }, { 'name': 'C', 'type': ['long', 'null'], 'default': None }, { 'name': 'D', 'type': ['long', 'string'] }] }),
		(BasicModelCustomNamespace, { 'namespace': 'custom_namespace', 'name': 'BasicModelCustomNamespace', 'type': 'record', 'fields': [{ 'name': 'A', 'type': 'long' }] }),
		(NestedModelCustomNamespace, { 'namespace': 'NestedModelCustomNamespace', 'name': 'NestedModelCustomNamespace', 'type': 'record', 'fields': [{ 'name': 'A', 'type': { 'namespace': 'NestedModelCustomNamespace', 'name': 'BasicModelCustomNamespace', 'type': 'record', 'fields': [{ 'name': 'A', 'type': 'long' }] } }] }),
		(Error, { 'namespace': 'Error', 'name': 'Error', 'type': 'error', 'fields': [{ 'name': 'refid', 'type': ['null', { 'type': 'fixed', 'name': 'RefId', 'size': 16 }] }, { 'name': 'status', 'type': 'long' }, { 'name': 'error', 'type': 'string' }] }),
		(ValidationError, { 'namespace': 'ValidationError', 'name': 'ValidationError', 'type': 'error', 'fields': [{ 'name': 'detail', 'type': { 'items': { 'fields': [{ 'name': 'loc', 'type': { 'items': 'string', 'namespace': 'ValidationError', 'type': 'array' } }, { 'name': 'msg', 'type': 'string' }, { 'name': 'type', 'type': 'string' }], 'name': 'ValidationErrorDetail', 'namespace': 'ValidationError', 'type': 'record' }, 'namespace': 'ValidationError', 'type': 'array' } }] })
	],
)
def test_ConvertSchema_ValidInputError_ModelConvertedSuccessfully(input_model: Type[BaseModel], expected: dict) :

	# act
	schema: dict = convert_schema(input_model)

	# assert
	assert expected == schema


@pytest.mark.parametrize(
	'input_model, expected', [
		(BasicModelBaseTypes, { 'namespace': 'BasicModelBaseTypes', 'name': 'BasicModelBaseTypes', 'type': 'error', 'fields': [{ 'name': 'A', 'type': 'string' }, { 'name': 'B', 'type': 'long' }, { 'name': 'C', 'type': 'double' }, { 'name': 'D', 'type': 'bytes' }, { 'name': 'E', 'type': 'boolean' }] }),
		(BasicModelAdvancedTypes, { 'namespace': 'BasicModelAdvancedTypes', 'name': 'BasicModelAdvancedTypes', 'type': 'error', 'fields': [{ 'name': 'A', 'type': { 'type': 'long', 'logicalType': 'timestamp-micros' } }, { 'name': 'B', 'type': { 'name': 'Bytes_10', 'type': 'fixed', 'size': 10 } }, { 'name': 'C', 'type': { 'type': 'bytes', 'logicalType': 'decimal', 'precision': 5, 'scale': 3 } }, { 'name': 'D', 'type': { 'name': 'BasicEnum', 'type': 'enum', 'symbols': ['TEST1', 'TEST2', 'TEST3'] } }, { 'name': 'E', 'type': { 'type': 'int', 'logicalType': 'date' } }, { 'name': 'F', 'type': { 'type': 'long', 'logicalType': 'time-micros' } }] }),
		(NestedModelBasicTypes, { 'namespace': 'NestedModelBasicTypes', 'name': 'NestedModelBasicTypes', 'type': 'error', 'fields': [{ 'name': 'A', 'type': { 'namespace': 'NestedModelBasicTypes', 'name': 'BasicModelBaseTypes', 'type': 'record', 'fields': [{ 'name': 'A', 'type': 'string' }, { 'name': 'B', 'type': 'long' }, { 'name': 'C', 'type': 'double' }, { 'name': 'D', 'type': 'bytes' }, { 'name': 'E', 'type': 'boolean' }] } }, { 'name': 'B', 'type': 'long' }] }),
		(BasicModelTypingTypes, { 'namespace': 'BasicModelTypingTypes', 'name': 'BasicModelTypingTypes', 'type': 'error', 'fields': [{ 'name': 'A', 'type': { 'type': 'array', 'namespace': 'BasicModelTypingTypes', 'items': 'long' } }, { 'name': 'B', 'type': { 'type': 'map', 'values': 'long' } }, { 'name': 'C', 'type': ['long', 'null'], 'default': None }, { 'name': 'D', 'type': ['long', 'string'] }] }),
		(BasicModelCustomNamespace, { 'namespace': 'custom_namespace', 'name': 'BasicModelCustomNamespace', 'type': 'error', 'fields': [{ 'name': 'A', 'type': 'long' }] }),
		(NestedModelCustomNamespace, { 'namespace': 'NestedModelCustomNamespace', 'name': 'NestedModelCustomNamespace', 'type': 'error', 'fields': [{ 'name': 'A', 'type': { 'namespace': 'NestedModelCustomNamespace', 'name': 'BasicModelCustomNamespace', 'type': 'record', 'fields': [{ 'name': 'A', 'type': 'long' }] } }] }),
		(Error, { 'namespace': 'Error', 'name': 'Error', 'type': 'error', 'fields': [{ 'name': 'refid', 'type': ['null', { 'type': 'fixed', 'name': 'RefId', 'size': 16 }] }, { 'name': 'status', 'type': 'long' }, { 'name': 'error', 'type': 'string' }] }),
		(ValidationError, { 'namespace': 'ValidationError', 'name': 'ValidationError', 'type': 'error', 'fields': [{ 'name': 'detail', 'type': { 'items': { 'fields': [{ 'name': 'loc', 'type': { 'items': 'string', 'namespace': 'ValidationError', 'type': 'array' } }, { 'name': 'msg', 'type': 'string' }, { 'name': 'type', 'type': 'string' }], 'name': 'ValidationErrorDetail', 'namespace': 'ValidationError', 'type': 'record' }, 'namespace': 'ValidationError', 'type': 'array' } }] })
	],
)
def test_ConvertSchema_ValidInputError_ErrorModelConvertedSuccessfully(input_model: Type[BaseModel], expected: dict) :

	# act
	schema: dict = convert_schema(input_model, error=True)

	# assert
	assert expected == schema


class BasicModelInvalidType1(BaseModel) :
	A: Decimal


class BasicModelInvalidType2(BaseModel) :
	A: dict


class BasicModelInvalidType3(BaseModel) :
	A: condecimal(max_digits=10)


class BasicModelInvalidType4(BaseModel) :
	A: condecimal(decimal_places=10)


class BasicModelInvalidType5(BaseModel) :
	A: Dict[int, int]


class BasicModelInvalidType6(BaseModel) :
	A: condecimal(decimal_places=10)


class BasicModelInvalidType7(Enum) :
	test1: str = 'TEST1'
	test2: str = 'TEST2'
	test3: str = 'TEST1'


@pytest.mark.parametrize(
	'input_model', [
		BasicModelInvalidType1,
		BasicModelInvalidType2,
		BasicModelInvalidType3,
		BasicModelInvalidType4,
		BasicModelInvalidType5,
		BasicModelInvalidType6,
		BasicModelInvalidType7,
	],
)
def test_ConvertSchema_InvalidModel_ConvertSchemaThrowsError(input_model: Type[BaseModel]) :

	# assert
	with raises(AvroException) :
		convert_schema(input_model)


# this is a special case, these schemas are defined by the apache organtization and the schemas generated by convert_schema MUST match
# https://avro.apache.org/docs/current/spec.html#handshake
from kh_common.avro.handshake import HandshakeRequest, HandshakeResponse


@pytest.mark.parametrize(
	'input_model, expected', [
		(HandshakeRequest, {
			'type': 'record',
			'name': 'HandshakeRequest', 'namespace':'org.apache.avro.ipc',
			'fields': [
				{ 'name': 'clientHash', 'type': { 'type': 'fixed', 'name': 'MD5', 'size': 16 } },
				{ 'name': 'clientProtocol', 'type': ['null', 'string'] },
				{ 'name': 'serverHash', 'type': 'MD5' },
				{ 'name': 'meta', 'type': ['null', { 'type': 'map', 'values': 'bytes' }] }
			]
		}),
		(HandshakeResponse, {
			'type': 'record',
			'name': 'HandshakeResponse', 'namespace': 'org.apache.avro.ipc',
			'fields': [
				{ 'name': 'match', 'type': { 'type': 'enum', 'name': 'HandshakeMatch', 'symbols': ['BOTH', 'CLIENT', 'NONE'] } },
				{ 'name': 'serverProtocol', 'type': ['null', 'string'] },
				{ 'name': 'serverHash', 'type': ['null', { 'type': 'fixed', 'name': 'MD5', 'size': 16 }] },
				{ 'name': 'meta', 'type': ['null', { 'type': 'map', 'values': 'bytes' }] }
			]
		}),
	],
)
def test_ConvertSchema_HandshakeModels_HandshakeConvertedSuccessfully(input_model: Type[BaseModel], expected: dict) :

	# act
	schema: dict = convert_schema(input_model)

	# assert
	assert expected == schema
