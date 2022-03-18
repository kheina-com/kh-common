from pydantic import BaseModel, conint, ConstrainedBytes, ConstrainedDecimal, ConstrainedInt
from typing import Any, Callable, Dict, Iterable, List, Optional, Type, Union
from datetime import date, datetime, time
from avro.errors import AvroException
from decimal import Decimal
from enum import Enum
from uuid import UUID


AvroInt: ConstrainedInt = conint(ge=-2147483648, le=2147483647)


class AvroFloat(float) :
	pass


AvroSchema: Type = Union[str, Dict[str, Union['AvroSchema', int]], List['AvroSchema']]


def convert_schema(model: Type[BaseModel], error: bool = False) -> AvroSchema :
	namespace: Union[None, str] = getattr(model, '__namespace__', None)
	name: str = get_name(model)
	error: bool = error or name.lower().endswith('error')
	avro_schema: AvroSchema = _get_type(model, set(), namespace or name)

	if isinstance(avro_schema, dict) :
		avro_schema['name'] = name

		if error :
			avro_schema['type'] = 'error'

	return avro_schema


def get_name(model: Type[BaseModel]) -> str :
	origin = getattr(model, '__origin__', None)  # for types from typing library

	if origin :
		return str(origin) + '_' + '_'.join(list(map(get_name, model.__args__)))

	if issubclass(model, ConstrainedBytes) and model.__name__ == 'ConstrainedBytesValue' :
		return 'Bytes_' + str(model.max_length)

	if issubclass(model, ConstrainedDecimal) and model.__name__ == 'ConstrainedDecimalValue' :
		return f'Decimal_{model.max_digits}_{model.decimal_places}'

	return model.__name__


def _convert_array(model: Type[Iterable[Any]], refs: set, namespace: str) -> Dict[str, AvroSchema] :
	object_type: AvroSchema = _get_type(model.__args__[0], refs, namespace)

	# optimize: does this do anything?
	if (
		isinstance(object_type, dict)
		and isinstance(object_type.get('type'), dict)
		and object_type['type'].get('logicalType') is not None
	):
		object_type = object_type['type']

	return {
		'type': 'array',
		'namespace': namespace,
		'items': object_type,
	}


def _convert_object(model: Type[BaseModel], refs: set, namespace: str) -> Dict[str, Union[str, List[AvroSchema]]] :
	fields = []

	for name, field in model.__fields__.items() :
		submodel = model.__annotations__[name]
		f: AvroSchema = { 'name': name }

		if getattr(submodel, '__origin__', None) is Union and len(submodel.__args__) == 2 and type(None) in submodel.__args__ and field.default is None :
			# this is a special case where the field is nullable and the default value is null, but the actual value can be omitted from the schema
			# we rearrange Optional[Type] and Union[Type, None] to Union[None, Type] so that null becomes the default type and the 'default' key is unnecessary
			type_index: int = 0 if submodel.__args__.index(type(None)) else 1
			f['type'] = _get_type(Union[None, submodel.__args__[type_index]], refs, namespace)

		else :
			f['type'] = _get_type(submodel, refs, namespace)

			if not field.required :
				# optimize: does this value need to be avro-encoded?
				f['default'] = field.default

		fields.append(f)

	return {
		'type': 'record',
		'name': get_name(model),
		'namespace': namespace,
		'fields': fields,
	}


def _convert_union(model: Type[Union[Any, Any]], refs: set, namespace: str) -> List[AvroSchema] :
	return list(map(lambda x : _get_type(x, refs, namespace), model.__args__))


def _convert_enum(model: Type[Enum], refs: set, namespace: str) -> Dict[str, Union[str, List[str]]] :
	if len(model.__members__.values()) != len(set(model.__members__.values())) :
		raise AvroException('enums must contain all unique values to be avro encoded')

	return {
		'type': 'enum',
		'name': get_name(model),
		'symbols': list(map(lambda x : x.value, model.__members__.values())),
	}


def _convert_bytes(model: Type[ConstrainedBytes], refs: set, namespace: str) -> Dict[str, Union[str, int]] :
	if model.min_length == model.max_length and model.max_length :
		return {
			'type': 'fixed',
			'name': get_name(model),
			'size': model.max_length,
		}

	return 'bytes'


def _convert_map(model: Type[Dict[str, Any]], refs: set, namespace: str) -> Dict[str, AvroSchema] :
	if not hasattr(model, '__args__') :
		raise AvroException('typing.Dict must be used to determine key/value type, not dict')

	if model.__args__[0] != str :
		raise AvroException('maps must have string keys')

	return {
		'type': 'map',
		'values': _get_type(model.__args__[1], refs, namespace),
	}


def _convert_decimal(model: Type[Decimal], refs: set, namespace: str) -> None :
	raise AvroException('Support for unconstrained decimals is not possible due to the nature of avro decimals. please use pydantic.condecimal(max_digits=int, decimal_places=int)')


def _convert_condecimal(model: Type[ConstrainedDecimal], refs: set, namespace: str) -> Dict[str, Union[str, int]] :
	if not model.max_digits or model.decimal_places is None :
		raise AvroException('Decimal attributes max_digits and decimal_places must be provided in order to map to avro decimals')

	return {
		'type': 'bytes',
		'logicalType': 'decimal',
		'precision': model.max_digits,
		'scale': model.decimal_places,
	}


_conversions_ = {
	BaseModel: _convert_object,
	Union: _convert_union,
	list: _convert_array,
	Enum: _convert_enum,
	ConstrainedBytes: _convert_bytes,
	Dict: _convert_map,
	dict: _convert_map,
	Decimal: _convert_decimal,
	ConstrainedDecimal: _convert_condecimal,
	bool: 'boolean',
	AvroInt: 'int',
	int: 'long',
	AvroFloat: 'float',
	float: 'double',
	bytes: 'bytes',
	type(None): 'null',
	str: 'string',
	datetime: {
		'type': 'long',
		'logicalType': 'timestamp-micros',
	},
	date: {
		'type': 'int',
		'logicalType': 'date',
	},
	time: {
		'type': 'long',
		'logicalType': 'time-micros',
	},
	UUID: {
		'type': 'string',
		'logicalType': 'uuid',
	},
}


def _get_type(model: Type[BaseModel], refs: set, namespace: str) -> AvroSchema :
	model_name: str = get_name(model)

	if model_name in refs :
		return model_name

	origin: Optional[Type] = getattr(model, '__origin__', None)

	if origin in _conversions_ :
		# none of these can be converted without funcs
		t: AvroSchema = _conversions_[origin](model, refs, namespace)
		if isinstance(t, dict) and 'name' in t :
			refs.add(t['name'])
		return t

	for cls in model.__mro__ :
		if cls in _conversions_ :
			if isinstance(_conversions_[cls], Callable) :
				t: AvroSchema = _conversions_[cls](model, refs, namespace)
				if 'name' in t :
					refs.add(t['name'])
				return t
			return _conversions_[cls]

	raise NotImplementedError(f'{model} missing from conversion map.')
