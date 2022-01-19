from avro.io import BinaryDecoder, BinaryEncoder, DatumReader
from kh_common.avro.serialization import ABetterDatumWriter
from kh_common.avro.schema import convert_schema
from pydantic import BaseModel, parse_obj_as
from avro.schema import parse, Schema
from typing import Type, Union
from io import BytesIO, FileIO
from json import dumps


class AvroSerializer :

	def __init__(self, model: Type[BaseModel]) :
		schema: Schema = parse(dumps(convert_schema(model)))
		self._writer: ABetterDatumWriter = ABetterDatumWriter(schema)


	def __call__(self, data: BaseModel) :
		io_object: BytesIO = BytesIO()
		encoder: BinaryEncoder = BinaryEncoder(io_object)
		self._writer.write_data(self._writer.writers_schema, data.dict() if isinstance(data, BaseModel) else list(map(BaseModel.dict, data)), encoder)
		return io_object.getvalue()


class AvroDeserializer :

	def __init__(self, read_model: Type[BaseModel], write_model: Union[Type[BaseModel], FileIO] = None) :
		self._reader: DatumReader
		self._model: Type[BaseModel] = read_model
		read_schema = parse(dumps(convert_schema(read_model)))
		write_schema: Schema

		if not write_model :
			write_schema = read_schema

		elif issubclass(write_model, BaseModel) :
			write_schema = parse(dumps(convert_schema(write_model)))

		else :
			write_schema = parse(write_model.read())

		self._reader = DatumReader(write_schema, read_schema)


	def __call__(self, data: bytes) :
		return parse_obj_as(self._model, self._reader.read(BinaryDecoder(BytesIO(data))))
