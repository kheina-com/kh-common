from kh_common.logging import LogHandler; LogHandler.logging_available = False
from kh_common.avro import AvroSerializer, AvroDeserializer
from pydantic import BaseModel, conbytes, condecimal
from typing import Dict, List, Optional, Type, Union
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


@pytest.mark.parametrize(
	'input_model', [
		BasicModelBaseTypes(A='string', B=1, C=1.1, D=b'abc'),
		BasicModelAdvancedTypes(A=datetime.now(), B='abcde12345', C=Decimal('12.345'), D=BasicEnum.test2),
		NestedModelBasicTypes(A=BasicModelBaseTypes(A='string', B=1, C=1.1, D=b'abc'), B=2),
		BasicModelTypingTypes(A=[1], B={ 'a': 2 }, C=None, D=3),
		BasicModelTypingTypes(A=[1], B={ 'a': 2 }, C=None, D='3'),
	],
)
def test_serialize_ValidInput_ModelEncodedAndDecodedSuccessfully(input_model: BaseModel) :

	# arrange
	serializer: AvroSerializer = AvroSerializer(type(input_model))
	deserializer: AvroDeserializer = AvroDeserializer(type(input_model))

	# act
	result = deserializer(serializer(input_model))

	# assert
	assert result == input_model


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
		AvroSerializer(input_model)