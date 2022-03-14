from avro.io import BinaryDecoder, BinaryEncoder, DatumReader
from kh_common.avro.serialization import ABetterDatumWriter
from avro.schema import Schema, parse as parse_avro_schema
from kh_common.avro.schema import convert_schema
from pydantic import BaseModel, parse_obj_as
from typing import Callable, Type, Union
from json import dumps
from io import BytesIO


def avro_frame(bytes_to_frame: bytes = None) -> bytes :
	if bytes_to_frame :
		return len(bytes_to_frame).to_bytes(4, 'big') + bytes_to_frame

	return b'\x00\x00\x00\x00'


def read_avro_frames(avro_bytes: bytes) -> bytes :
	while avro_bytes :
		frame_len = int.from_bytes(avro_bytes[:4], 'big') + 4
		yield avro_bytes[4:frame_len]
		avro_bytes = avro_bytes[frame_len:]


_data_converter_map = {
	dict: lambda d : d,
	list: lambda d : list(map(BaseModel.dict, d)),
	tuple: lambda d : list(map(BaseModel.dict, d)),
	BaseModel: BaseModel.dict,
}


class AvroSerializer :

	def __init__(self, model: Union[Schema, Type[BaseModel]]) :
		schema: Schema = model if isinstance(model, Schema) else parse_avro_schema(dumps(convert_schema(model)))
		self._writer: ABetterDatumWriter = ABetterDatumWriter(schema)


	def __call__(self, data: BaseModel) :
		io_object: BytesIO = BytesIO()
		encoder: BinaryEncoder = BinaryEncoder(io_object)

		for cls in type(data).__mro__ :
			if cls in _data_converter_map :
				self._writer.write_data(self._writer.writers_schema, _data_converter_map[cls](data), encoder)
				return io_object.getvalue()

		raise NotImplementedError(f'unable to convert "{type(data)}" for encoding')


class AvroDeserializer :

	def __init__(self, read_model: Type[BaseModel] = None, read_schema: Union[Schema, str] = None, write_model: Union[Schema, Type[BaseModel], str] = None, parse: bool = True) :
		assert read_model or (read_schema and parse == False), 'either read_model or read_schema must be provided. if only read schema is provided, parse must be false'
		write_schema: Schema

		if not read_schema :
			read_schema = parse_avro_schema(dumps(convert_schema(read_model)))

		elif isinstance(read_schema, str) :
			read_schema = parse_avro_schema(read_schema)

		elif not isinstance(read_schema, Schema) :
			raise NotImplementedError(f'the type for read_schema "{type(read_schema)}" is not supported.')


		if not write_model :
			write_schema = read_schema

		elif isinstance(write_model, Schema) :
			write_schema = write_model

		elif isinstance(write_model, str) :
			write_schema = parse_avro_schema(write_model)

		elif issubclass(write_model, BaseModel) :
			write_schema = parse_avro_schema(dumps(convert_schema(write_model)))

		else :
			raise NotImplementedError(f'the type for write_model "{type(write_model)}" is not supported.')

		reader: DatumReader = DatumReader(write_schema, read_schema)

		if parse :
			self._parser: Callable[[bytes], read_model] = lambda x : parse_obj_as(read_model, reader.read(x))

		else :
			self._parser: Callable[[bytes], dict] = reader.read


	def __call__(self, data: bytes) :
		return self._parser(BinaryDecoder(BytesIO(data)))
