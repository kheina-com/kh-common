from avro.io import BinaryDecoder, BinaryEncoder, DatumReader
from kh_common.avro.serialization import ABetterDatumWriter
from kh_common.avro.schema import convert_schema
from pydantic import BaseModel, parse_obj_as
from avro.schema import parse, Schema
from typing import Type, Union
from io import BytesIO, FileIO
from json import dumps


def avro_frame(bytes_to_frame: bytes = None) -> bytes :
	if bytes_to_frame :
		return len(bytes_to_frame).to_bytes(4, 'big') + bytes_to_frame

	return b'\x00\x00\x00\x00'


def read_avro_frames(avro_bytes: bytes) -> bytes :
	while avro_bytes :
		frame_len = int.from_bytes(avro_bytes[:4], 'big') + 4
		yield avro_bytes[4:frame_len]
		avro_bytes = avro_bytes[frame_len:]


class AvroSerializer :

	def __init__(self, model: Union[Schema, Type[BaseModel]]) :
		schema: Schema = model if isinstance(model, Schema) else parse(dumps(convert_schema(model)))
		self._writer: ABetterDatumWriter = ABetterDatumWriter(schema)


	def __call__(self, data: BaseModel) :
		io_object: BytesIO = BytesIO()
		encoder: BinaryEncoder = BinaryEncoder(io_object)
		self._writer.write_data(self._writer.writers_schema, data.dict() if isinstance(data, BaseModel) else list(map(BaseModel.dict, data)), encoder)
		return io_object.getvalue()


class AvroDeserializer :

	def __init__(self, read_model: Type[BaseModel], read_schema: Union[Schema, str] = None, write_model: Union[Schema, Type[BaseModel], str] = None) :
		self._reader: DatumReader
		self._model: Type[BaseModel] = read_model
		write_schema: Schema

		if not read_schema :
			read_schema = parse(dumps(convert_schema(read_model)))

		elif isinstance(read_schema, str) :
			read_schema = parse(read_schema)

		elif not isinstance(read_schema, Schema) :
			raise NotImplementedError(f'the type for read_schema "{type(read_schema)} is not supported.')


		if not write_model :
			write_schema = read_schema

		elif isinstance(write_model, Schema) :
			write_schema = write_model

		elif isinstance(write_model, str) :
			write_schema = parse(write_model)

		elif issubclass(write_model, BaseModel) :
			write_schema = parse(dumps(convert_schema(write_model)))

		else :
			raise NotImplementedError(f'the type for write_model "{type(write_model)} is not supported.')

		self._reader = DatumReader(write_schema, read_schema)


	def __call__(self, data: bytes) :
		return parse_obj_as(self._model, self._reader.read(BinaryDecoder(BytesIO(data))))
