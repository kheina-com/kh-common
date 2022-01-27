from kh_common.logging import LogHandler; LogHandler.logging_available = False
from pydantic import BaseModel, conbytes, condecimal
from typing import Dict, List, Optional, Type, Union
from kh_common.avro.schema import convert_schema
from kh_common.datetime import datetime
from avro.errors import AvroException
from decimal import Decimal
from pytest import raises
from enum import Enum
import pytest


class BasicModelBaseTypes(BaseModel) :
	A: str
	B: int
	C: float
	D: bytes


class BasicEnum(Enum) :
	test1: str = 'TEST1'
	test2: str = 'TEST2'
	test3: str = 'TEST3'


class BasicModelAdvancedTypes(BaseModel) :
	A: datetime
	B: conbytes(max_length=10, min_length=10)
	C: condecimal(max_digits=5, decimal_places=3)
	D: BasicEnum


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
		(BasicModelBaseTypes, { 'namespace': 'BasicModelBaseTypes', 'name': 'BasicModelBaseTypes', 'type': 'record', 'fields': [{ 'name': 'A', 'type': 'string' }, { 'name': 'B', 'type': 'long' }, { 'name': 'C', 'type': 'double' }, { 'name': 'D', 'type': 'bytes' }] }),
		(BasicModelAdvancedTypes, { 'namespace': 'BasicModelAdvancedTypes', 'name': 'BasicModelAdvancedTypes', 'type': 'record', 'fields': [{ 'name': 'A', 'type': { 'type': 'long', 'logicalType': 'timestamp-micros' } }, { 'name': 'B', 'type': { 'name': 'Bytes_10', 'type': 'fixed', 'size': 10 } }, { 'name': 'C', 'type': { 'type': 'bytes', 'logicalType': 'decimal', 'precision': 5, 'scale': 3 } }, { 'name': 'D', 'type': { 'name': 'BasicEnum', 'type': 'enum', 'symbols': ['TEST1', 'TEST2', 'TEST3'] } }] }),
		(NestedModelBasicTypes, { 'namespace': 'NestedModelBasicTypes', 'name': 'NestedModelBasicTypes', 'type': 'record', 'fields': [{ 'name': 'A', 'type': { 'namespace': 'NestedModelBasicTypes', 'name': 'BasicModelBaseTypes', 'type': 'record', 'fields': [{ 'name': 'A', 'type': 'string' }, { 'name': 'B', 'type': 'long' }, { 'name': 'C', 'type': 'double' }, { 'name': 'D', 'type': 'bytes' }] } }, { 'name': 'B', 'type': 'long' }] }),
		(BasicModelTypingTypes, { 'namespace': 'BasicModelTypingTypes', 'name': 'BasicModelTypingTypes', 'type': 'record', 'fields': [{ 'name': 'A', 'type': { 'type': 'array', 'namespace': 'BasicModelTypingTypes', 'items': 'long' } }, { 'name': 'B', 'type': { 'type': 'map', 'values': 'long' } }, { 'name': 'C', 'type': ['long', 'null'], 'default': None }, { 'name': 'D', 'type': ['long', 'string'] }] }),
		(BasicModelCustomNamespace, { 'namespace': 'custom_namespace', 'name': 'BasicModelCustomNamespace', 'type': 'record', 'fields': [{ 'name': 'A', 'type': 'long' }] }),
		(NestedModelCustomNamespace, { 'namespace': 'NestedModelCustomNamespace', 'name': 'NestedModelCustomNamespace', 'type': 'record', 'fields': [{ 'name': 'A', 'type': { 'namespace': 'NestedModelCustomNamespace', 'name': 'BasicModelCustomNamespace', 'type': 'record', 'fields': [{ 'name': 'A', 'type': 'long' }] } }] }),
	],
)
def test_serialize_ValidInput_ModelEncodedAndDecodedSuccessfully(input_model: Type[BaseModel], expected: dict) :

	# act
	schema: dict = convert_schema(input_model)

	# assert
	assert expected == schema


@pytest.mark.parametrize(
	'input_model, expected', [
		(BasicModelBaseTypes, { 'namespace': 'BasicModelBaseTypes', 'name': 'BasicModelBaseTypes', 'type': 'error', 'fields': [{ 'name': 'A', 'type': 'string' }, { 'name': 'B', 'type': 'long' }, { 'name': 'C', 'type': 'double' }, { 'name': 'D', 'type': 'bytes' }] }),
		(BasicModelAdvancedTypes, { 'namespace': 'BasicModelAdvancedTypes', 'name': 'BasicModelAdvancedTypes', 'type': 'error', 'fields': [{ 'name': 'A', 'type': { 'type': 'long', 'logicalType': 'timestamp-micros' } }, { 'name': 'B', 'type': { 'name': 'Bytes_10', 'type': 'fixed', 'size': 10 } }, { 'name': 'C', 'type': { 'type': 'bytes', 'logicalType': 'decimal', 'precision': 5, 'scale': 3 } }, { 'name': 'D', 'type': { 'name': 'BasicEnum', 'type': 'enum', 'symbols': ['TEST1', 'TEST2', 'TEST3'] } }] }),
		(NestedModelBasicTypes, { 'namespace': 'NestedModelBasicTypes', 'name': 'NestedModelBasicTypes', 'type': 'error', 'fields': [{ 'name': 'A', 'type': { 'namespace': 'NestedModelBasicTypes', 'name': 'BasicModelBaseTypes', 'type': 'record', 'fields': [{ 'name': 'A', 'type': 'string' }, { 'name': 'B', 'type': 'long' }, { 'name': 'C', 'type': 'double' }, { 'name': 'D', 'type': 'bytes' }] } }, { 'name': 'B', 'type': 'long' }] }),
		(BasicModelTypingTypes, { 'namespace': 'BasicModelTypingTypes', 'name': 'BasicModelTypingTypes', 'type': 'error', 'fields': [{ 'name': 'A', 'type': { 'type': 'array', 'namespace': 'BasicModelTypingTypes', 'items': 'long' } }, { 'name': 'B', 'type': { 'type': 'map', 'values': 'long' } }, { 'name': 'C', 'type': ['long', 'null'], 'default': None }, { 'name': 'D', 'type': ['long', 'string'] }] }),
		(BasicModelCustomNamespace, { 'namespace': 'custom_namespace', 'name': 'BasicModelCustomNamespace', 'type': 'error', 'fields': [{ 'name': 'A', 'type': 'long' }] }),
		(NestedModelCustomNamespace, { 'namespace': 'NestedModelCustomNamespace', 'name': 'NestedModelCustomNamespace', 'type': 'error', 'fields': [{ 'name': 'A', 'type': { 'namespace': 'NestedModelCustomNamespace', 'name': 'BasicModelCustomNamespace', 'type': 'record', 'fields': [{ 'name': 'A', 'type': 'long' }] } }] }),
	],
)
def test_serialize_ValidInputError_ModelEncodedAndDecodedSuccessfully(input_model: Type[BaseModel], expected: dict) :

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
def test_serialize_InvalidModel_SerializerThrowsError(input_model: Type[BaseModel]) :

	# assert
	with raises(AvroException) :
		convert_schema(input_model)
