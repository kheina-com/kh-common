from kh_common.logging import LogHandler; LogHandler.logging_available = False
from kh_common.avro import AvroDeserializer, AvroSerializer, read_avro_frames
from kh_common.avro.handshake import CallResponse, HandshakeRequest
from kh_common.avro.routing import AvroRoute
from fastapi.testclient import TestClient
from pydantic import BaseModel
from fastapi import FastAPI
import pytest


endpoint = '/'
base_url = 'dev.kheina.com'
schema = 'https://'


class ResponseModel(BaseModel) :
	result: bool

model_deserializer: AvroDeserializer = AvroDeserializer(ResponseModel)
call_deserializer: AvroDeserializer = AvroDeserializer(CallResponse)

handshake_serializer: AvroSerializer = AvroSerializer(HandshakeRequest)


def get_second_frame(response: bytes) :
	frames = read_avro_frames(response)
	next(frames)
	return next(frames)


@pytest.mark.asyncio
class TestAvroServer :

	def test_AvroRoute_GetNoHeaders_ReturnsJson(self) :

		# arrange
		app = FastAPI()
		app.router.route_class = AvroRoute

		@app.post(endpoint, response_model=ResponseModel)
		async def test_func() :
			return ResponseModel(
				result=True,
			)

		client = TestClient(app, base_url=base_url)

		# act
		response = client.post(schema + base_url + endpoint)

		# assert
		assert 200 == response.status_code
		assert { 'result': True } == response.json()


	def test_AvroRoute_AvroHeaders_ReturnsAvro(self) :

		# arrange
		app = FastAPI()
		app.router.route_class = AvroRoute

		@app.post(endpoint, response_model=ResponseModel)
		async def test_func() :
			return ResponseModel(
				result=True,
			)

		client = TestClient(app, base_url=base_url)

		# act
		response = client.post(
			schema + base_url + endpoint,
			headers={ 'accept': 'avro/binary' },
			data=handshake_serializer(HandshakeRequest(clientHash=b'deadbeefdeadbeef', serverHash=b'deadbeefdeadbeef'))
		)

		from kh_common.avro.handshake import HandshakeResponse
		from kh_common.models import Error

		# assert
		assert 200 == response.status_code
		assert ResponseModel(result=True) == model_deserializer(call_deserializer(next(read_avro_frames(response._content))).response)
