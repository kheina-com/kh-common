from pydantic import BaseModel, ConstrainedBytes, ConstrainedDecimal
from typing import Any, Callable, Dict, Iterable, List, Type, Union
from avro.errors import AvroException
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID


def convert_schema(model: Type[BaseModel], error: bool = False) -> dict :
	namespace: Union[None, str] = getattr(model, '__namespace__', None)
	name: str = _get_name(model)
	avro_schema: dict = _get_type(model, set(), namespace or name)

	if isinstance(avro_schema, dict) :
		avro_schema['name'] = name

		if error :
			avro_schema['type'] = 'error'

	return avro_schema


def _get_name(model: Type[BaseModel]) -> str :
	origin = getattr(model, '__origin__', None)  # for types from typing library

	if origin :
		return str(origin) + '_' + '_'.join(list(map(_get_name, model.__args__)))

	if issubclass(model, ConstrainedBytes) and model.__name__ == 'ConstrainedBytesValue' :
		return 'Bytes_' + str(model.max_length)

	if issubclass(model, ConstrainedDecimal) and model.__name__ == 'ConstrainedDecimalValue' :
		return 'Decimal_' + '_'.join(list(map(str, [model.max_digits, model.decimal_places])))

	return model.__name__


def _convert_array(model: Type[Iterable[Any]], refs: set, namespace: str) -> dict :
	object_type = _get_type(model.__args__[0], refs, namespace)

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


def _convert_object(model: Type[BaseModel], refs: set, namespace: str) -> dict :
	fields = []

	for name, field in model.__fields__.items() :
		f = {
			'name': name,
			'type': _get_type(model.__annotations__[name], refs, namespace),
		}

		if not field.required :
			# optimize: does this value need to be avro-encoded?
			f['default'] = field.default

		fields.append(f)

	return {
		'type': 'record',
		'name': _get_name(model),
		'namespace': namespace,
		'fields': fields,
	}


def _convert_union(model: Type[Union[Any, Any]], refs: set, namespace: str) -> List[Union[dict, str]] :
	return list(map(lambda x : _get_type(x, refs, namespace), model.__args__))


def _convert_enum(model: Type[Enum], refs: set, namespace: str) -> dict :
	if len(model.__members__.values()) != len(set(model.__members__.values())) :
		raise AvroException('enums must contain all unique values to be avro encoded')

	return {
		'type': 'enum',
		'name': _get_name(model),
		'symbols': list(map(lambda x : x.value, model.__members__.values())),
	}


def _convert_bytes(model: Type[ConstrainedBytes], refs: set, namespace: str) -> Union[dict, str] :
	if model.min_length == model.max_length and model.max_length :
		return {
			'type': 'fixed',
			'name': _get_name(model),
			'size': model.max_length,
		}

	return 'bytes'


def _convert_map(model: Type[Dict[str, Any]], refs: set, namespace: str) -> dict :
	if not  hasattr(model, '__args__') :
		raise AvroException('typing.Dict must be used to determine key/value type, not dict')

	if model.__args__[0] != str :
		raise AvroException('maps must have string keys')

	return {
		'type': 'map',
		'values': _get_type(model.__args__[1], refs, namespace),
	}


def _convert_decimal(model: Type[Decimal], refs: set, namespace: str) -> None :
	raise AvroException('Support for unconstrained decimals is not possible due to the nature of avro decimals. please use pydantic.condecimal(max_digits=int, decimal_places=int)')


def _convert_condecimal(model: Type[ConstrainedDecimal], refs: set, namespace: str) -> dict :
	if not model.max_digits or not model.decimal_places :
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
	int: 'long',
	float: 'double',
	bytes: 'bytes',
	type(None): 'null',
	str: 'string',
	datetime: {
		'type': 'long',
		'logicalType': 'timestamp-micros',
	},
	UUID: {
		'type': 'string',
		'logicalType': 'uuid',
	},
	# optimize: are these necessary? do they map to any python/pydanitic types?
	# update: there are several pydantic date/time types that these can be mapped to
	# ('string', 'date'): {
	# 	'type': 'int',
	# 	'logicalType': 'date',
	# },
	# ('string', 'time'): {
	# 	'type': 'long',
	# 	'logicalType': 'time-micros',
	# },
}


def _get_type(model: Type[BaseModel], refs: set, namespace: str) -> Union[dict, str] :
	model_name = _get_name(model)

	if model_name in refs :
		return model_name

	origin = getattr(model, '__origin__', None)

	if origin in _conversions_ :
		# none of these can be converted without funcs
		t = _conversions_[origin](model, refs, namespace)
		if isinstance(t, dict) and 'name' in t :
			refs.add(t['name'])
		return t

	for cls in model.__mro__ :
		if cls in _conversions_ :
			if isinstance(_conversions_[cls], Callable) :
				t = _conversions_[cls](model, refs, namespace)
				if 'name' in t :
					refs.add(t['name'])
				return t
			return _conversions_[cls]

	raise NotImplementedError(f'{model} missing from conversion map.')
