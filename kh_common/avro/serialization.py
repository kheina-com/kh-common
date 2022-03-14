from avro.schema import ArraySchema, EnumSchema, FixedSchema, MapSchema, RecordSchema, Schema, UnionSchema
from avro.constants import DATE, DECIMAL, TIMESTAMP_MICROS, TIMESTAMP_MILLIS, TIME_MICROS, TIME_MILLIS
from avro.errors import AvroException, AvroTypeException, IgnoredLogicalType
from typing import Any, Dict, Mapping, Sequence, Union
from avro.io import BinaryEncoder, DatumWriter
from decimal import Decimal
from warnings import warn
from uuid import UUID
from enum import Enum
import datetime


def _validate_enum(self, datum: Union[Enum, str]) :
	"""
	Return self if datum is a valid member of this Enum, else None.
	python Enums are converted to their value
	"""
	datum: str = datum.value if isinstance(datum, Enum) else datum
	return self if datum in self.symbols else None


EnumSchema.validate = _validate_enum


class ABetterDatumWriter(DatumWriter) :

	def write_enum(self, writers_schema: EnumSchema, datum: Union[Enum, str], encoder: BinaryEncoder) -> None:
		"""
		An enum is encoded by a int, representing the zero-based position of the symbol in the schema.
		python Enums are converted to their value
		"""
		datum: str = datum.value if isinstance(datum, Enum) else datum
		index_of_datum = writers_schema.symbols.index(datum)
		return encoder.write_int(index_of_datum)


	def _writer_type_null_(writers_schema: Schema, datum: None, encoder: BinaryEncoder) -> None :
		if datum is None :
			return encoder.write_null(datum)
		raise AvroTypeException(writers_schema, datum)


	def _writer_type_bool_(writers_schema: Schema, datum: bool, encoder: BinaryEncoder) -> None :
		if isinstance(datum, bool) :
			return encoder.write_boolean(datum)
		raise AvroTypeException(writers_schema, datum)


	def _writer_type_str_(writers_schema: Schema, datum: Union[str, UUID], encoder: BinaryEncoder) -> None :
		if isinstance(datum, str) :
			return encoder.write_utf8(datum)

		elif isinstance(datum, UUID) :
			return encoder.write_utf8(str(datum))

		raise AvroTypeException(writers_schema, datum)


	def _writer_type_int_(writers_schema: Schema, datum: int, encoder: BinaryEncoder) -> None :
		logical_type = getattr(writers_schema, 'logical_type', None)

		if logical_type == DATE :
			if isinstance(datum, datetime.date) :
				return encoder.write_date_int(datum)
			warn(IgnoredLogicalType(f'{datum} is not a date type'))

		elif logical_type == TIME_MILLIS :
			if isinstance(datum, datetime.time) :
				return encoder.write_time_millis_int(datum)
			warn(IgnoredLogicalType(f'{datum} is not a time type'))

		if isinstance(datum, int) :
			return encoder.write_int(datum)

		raise AvroTypeException(writers_schema, datum)


	def _writer_type_float_(writers_schema: Schema, datum: Union[int, float], encoder: BinaryEncoder) -> None :
		if isinstance(datum, (int, float)) :
			return encoder.write_float(datum)
		raise AvroTypeException(writers_schema, datum)


	def _writer_type_double_(writers_schema: Schema, datum: Union[int, float], encoder: BinaryEncoder) -> None :
		if isinstance(datum, (int, float)) :
			return encoder.write_double(datum)
		raise AvroTypeException(writers_schema, datum)


	def _writer_type_long_(writers_schema: Schema, datum: int, encoder: BinaryEncoder) -> None :
		logical_type = getattr(writers_schema, 'logical_type', None)

		if logical_type == TIME_MICROS :
			if isinstance(datum, datetime.time) :
				return encoder.write_time_micros_long(datum)
			warn(IgnoredLogicalType(f'{datum} is not a time type'))

		elif logical_type == TIMESTAMP_MILLIS :
			if isinstance(datum, datetime.datetime) :
				return encoder.write_timestamp_millis_long(datum)
			warn(IgnoredLogicalType(f'{datum} is not a datetime type'))

		elif logical_type == TIMESTAMP_MICROS :
			if isinstance(datum, datetime.datetime) :
				return encoder.write_timestamp_micros_long(datum)
			warn(IgnoredLogicalType(f'{datum} is not a datetime type'))

		if isinstance(datum, int) :
			return encoder.write_long(datum)

		raise AvroTypeException(writers_schema, datum)


	def _writer_type_bytes_(writers_schema: Schema, datum: Union[Decimal, bytes], encoder: BinaryEncoder) -> None :
		logical_type = getattr(writers_schema, 'logical_type', None)

		if logical_type == DECIMAL :
			scale = writers_schema.get_prop('scale')

			if not (isinstance(scale, int) and scale > 0) :
				warn(IgnoredLogicalType(f'Invalid decimal scale {scale}. Must be a positive integer.'))

			elif not isinstance(datum, Decimal) :
				warn(IgnoredLogicalType(f'{datum} is not a decimal type'))

			elif not datum.same_quantum(Decimal(1) / 10 ** scale) :
				# round can be used here if we want to force all decimals to the correct scale
				# round(datum, scale)
				raise AvroTypeException(writers_schema, datum)

			else :
				return encoder.write_decimal_bytes(datum, scale)

		if isinstance(datum, bytes) :
			return encoder.write_bytes(datum)

		raise AvroTypeException(writers_schema, datum)


	def _writer_type_fixed_(self, writers_schema: Schema, datum: Union[Decimal, bytes], encoder: BinaryEncoder) -> None :
		logical_type = getattr(writers_schema, 'logical_type', None)

		if logical_type == DECIMAL :
			scale = writers_schema.get_prop('scale')

			if not (isinstance(scale, int) and scale > 0) :
				warn(IgnoredLogicalType(f'Invalid decimal scale {scale}. Must be a positive integer.'))

			elif not isinstance(datum, Decimal) :
				warn(IgnoredLogicalType(f'{datum} is not a decimal type'))

			elif not datum.same_quantum(Decimal(1) / 10 ** scale) :
				raise AvroTypeException(writers_schema, datum)

			else :
				return encoder.write_decimal_fixed(datum, scale, writers_schema.size)

		if isinstance(datum, bytes) :
			return self.write_fixed(writers_schema, datum, encoder)

		raise AvroTypeException(writers_schema, datum)


	def _writer_type_enum_(self, writers_schema: Schema, datum: Union[str, Enum], encoder: BinaryEncoder) -> None :
		if isinstance(datum, (str, Enum)) :
			return self.write_enum(writers_schema, datum, encoder)

		raise AvroTypeException(writers_schema, datum)


	def _writer_type_array_(self, writers_schema: Schema, datum: Sequence, encoder: BinaryEncoder) -> None :
		if isinstance(datum, Sequence) :
			return self.write_array(writers_schema, datum, encoder)
		raise AvroTypeException(writers_schema, datum)


	def _writer_type_map_schema_(self, writers_schema: Schema, datum: Dict[str, Any], encoder: BinaryEncoder) -> None :
		if isinstance(datum, Mapping) :
			return self.write_map(writers_schema, datum, encoder)
		raise AvroTypeException(writers_schema, datum)


	def _writer_type_record_(self, writers_schema: Schema, datum: dict, encoder: BinaryEncoder) -> None :
		if isinstance(datum, Mapping) :
			return self.write_record(writers_schema, datum, encoder)
		raise AvroTypeException(writers_schema, datum)


	_writer_type_map_ = {
		'null': _writer_type_null_,
		'boolean': _writer_type_bool_,
		'string': _writer_type_str_,
		'int': _writer_type_int_,
		'long': _writer_type_long_,
		'float': _writer_type_float_,
		'double': _writer_type_double_,
		'bytes': _writer_type_bytes_,
		FixedSchema: _writer_type_fixed_,
		EnumSchema: _writer_type_enum_,
		ArraySchema: _writer_type_array_,
		MapSchema: _writer_type_map_schema_,
		UnionSchema: DatumWriter.write_union,
		RecordSchema: _writer_type_record_,
	}


	def write_data(self, writers_schema: Schema, datum: Any, encoder: BinaryEncoder) -> None :
		# we're re-writing the function to dispatch writing datum, cause, frankly, theirs sucks

		if writers_schema.type in self._writer_type_map_ :
			return self._writer_type_map_[writers_schema.type](writers_schema, datum, encoder)

		for cls in type(writers_schema).__mro__ :
			if cls in self._writer_type_map_ :
				return self._writer_type_map_[cls](self, writers_schema, datum, encoder)

		raise AvroException(f'Unknown type: {writers_schema.type}')
