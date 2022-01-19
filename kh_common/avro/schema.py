from pydantic import BaseModel, schema_of
from typing import Callable, Tuple, Type


def convert_schema(model: Type[BaseModel]) -> dict :
	openapi_schema = schema_of(model)
	namespace = openapi_schema.get('title', model.__name__).replace('[', '_'). replace(']', '')
	avro_schema: dict = _get_type(openapi_schema, set(), openapi_schema.get('definitions', []), namespace)['type']
	avro_schema['name'] = namespace
	return avro_schema


def _convert_array(schema: dict, refs: set, defs: dict, namespace: str) :
	object_type = _get_type(schema['items'], refs, defs, namespace)

	# array of records
	if '$ref' in schema['items'] :
		object_type = object_type['type']

	# array of logical types
	if (
		isinstance(object_type, dict)
		and isinstance(object_type.get('type', {}), dict)
		and object_type.get('type', {}).get('logicalType') is not None
	):
		object_type = object_type['type']

	return {
		'type': 'array',
		'namespace': namespace,
		'items': object_type,
	}


def _convert_object(schema: dict, refs: set, defs: dict, namespace: str) :
	return {
		'type': 'record',
		'name': schema.get('name') or schema.get('title'),
		'namespace': namespace,
		'fields': _get_fields(schema, refs, defs, namespace),
	}

_conversions_ = {
	('array', None): _convert_array,
	('object', None): _convert_object,
	('boolean', None): 'boolean',
	('integer', None): 'long',
	('number', None): 'double',
	('string', None): 'string',
	('string', 'date-time'): {
		'type': 'long',
		'logicalType': 'timestamp-micros',
	},
	('string', 'date'): {
		'type': 'int',
		'logicalType': 'date',
	},
	('string', 'time'): {
		'type': 'long',
		'logicalType': 'time-micros',
	},
	('string', 'uuid'): {
		'type': 'string',
		'logicalType': 'uuid',
	},
}


def _get_type(schema: dict, refs: set, defs: dict, namespace: str) -> Tuple :
	avro_type = { }

	if 'default' in schema :
		avro_type['default'] = schema['default']

	key = (schema.get('type'), schema.get('format'))

	if '$ref' in schema :
		ref = schema['$ref'].replace('#/definitions/', '')

		if ref in refs :
			avro_type['type'] = ref

		else :
			avro_type = _get_type(defs[ref], refs, defs, namespace)
			refs.add(ref)

	elif 'enum' in schema :
		avro_type['type'] = {
			'type': 'enum',
			'name': schema['title'],
			'namespace': namespace,
			'symbols': schema['enum'],
		}

	elif key in _conversions_ :
		avro_type['type'] = _conversions_[key](schema, refs, defs, namespace) if isinstance(_conversions_[key], Callable) else _conversions_[key]

	else :
		raise NotImplementedError(f'{key[0]} with format {key[1]} missing from conversion map.')

	avro_type['name'] = schema.get('name') or schema.get('title')

	return avro_type


def _get_fields(schema: dict, refs: set, defs: dict, namespace: str) :
	required = set(schema.get('required', []))
	fields = []

	for key, value in schema.get('properties', {}).items():
		avro_type = _get_type(value, refs, defs, namespace)
		avro_type['name'] = key

		if key not in required:

			if 'default' not in avro_type :
				avro_type['type'] = [avro_type['type'], 'null']
				avro_type['default'] = None

			elif avro_type.get('default') is None :
				avro_type['type'] = [avro_type['type'], 'null']

		fields.append(avro_type)

	return fields
