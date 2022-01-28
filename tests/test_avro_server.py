from kh_common.logging import LogHandler; LogHandler.logging_available = False
from kh_common.avro.handshake import AvroMessage, AvroProtocol, CallResponse, HandshakeMatch, HandshakeRequest, HandshakeResponse
from kh_common.avro import AvroDeserializer, AvroSerializer, avro_frame, read_avro_frames
from kh_common.avro.schema import convert_schema
from kh_common.avro.routing import AvroRoute
from fastapi.testclient import TestClient
from kh_common.models import Error
from pydantic import BaseModel
from fastapi import FastAPI
from hashlib import md5
import pytest
import json


endpoint = '/'
base_url = 'dev.kheina.com'
schema = 'https://'


class ResponseModel(BaseModel) :
	result: bool

model_deserializer: AvroDeserializer = AvroDeserializer(ResponseModel)
call_deserializer: AvroDeserializer = AvroDeserializer(CallResponse)

handshake_serializer: AvroSerializer = AvroSerializer(HandshakeRequest)
handshake_deserializer: AvroDeserializer = AvroDeserializer(HandshakeResponse)


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


	@pytest.mark.parametrize(
		"payload",
		[
			None,
			avro_frame(handshake_serializer(HandshakeRequest(clientHash=b'deadbeefdeadbeef', serverHash=b'deadbeefdeadbeef'))),
			b'abc',  # valid body, but unable to be deserialized
		],
	)
	def test_AvroRoute_AllAvroHeadersInvalidHandshake_ReturnsAvroHandshake(self, payload: bytes) :

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
			headers={ 'accept': 'avro/binary', 'content-type': 'avro/binary' },
			data=payload,
		)


		# assert
		frame = read_avro_frames(response._content)
		assert 200 == response.status_code
		handshake: HandshakeResponse = handshake_deserializer(next(frame))
		assert HandshakeMatch.none == handshake.match
		assert handshake.serverHash == md5(handshake.serverProtocol.encode()).digest()
		assert json.loads(handshake.serverProtocol) == {
			'namespace': 'kh-common',
			'protocol': 'test_func__post',
			'messages': {
				'test_func__post': {
					'doc': 'the openapi description should go here. ex: V1Endpoint',
					'request': [],
					'response': ResponseModel.__name__,
					'errors': [Error.__name__],
					'oneWay': False,
					'types': [
						convert_schema(ResponseModel),
						convert_schema(Error, error=True),
					],
				},
			},
		}
		assert not next(frame)


	def test_AvroRoute_AllAvroHeadersValidHandshakeNoBody_ReturnsHandshakeAndResponse(self) :

		# arrange
		protocol = AvroProtocol(
			namespace='idk',
			protocol='idk',
			messages={
				'test_func__post': AvroMessage(
					types=[convert_schema(ResponseModel)],
					response=ResponseModel.__name__,
				),
			}
		).json()

		handshake = HandshakeRequest(
			clientHash=md5(protocol.encode()).digest(),
			serverHash=b'deadbeefdeadbeef',
			clientProtocol=protocol,
		)

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
			headers={ 'accept': 'avro/binary', 'content-type': 'avro/binary' },
			data=avro_frame(handshake_serializer(handshake)),
		)


		# assert
		frame = read_avro_frames(response._content)
		assert 200 == response.status_code
		handshake: HandshakeResponse = handshake_deserializer(next(frame))
		assert HandshakeMatch.client == handshake.match
		assert handshake.serverHash == md5(handshake.serverProtocol.encode()).digest()
		assert json.loads(handshake.serverProtocol) == {
			'namespace': 'kh-common',
			'protocol': 'test_func__post',
			'messages': {
				'test_func__post': {
					'doc': 'the openapi description should go here. ex: V1Endpoint',
					'request': [],
					'response': ResponseModel.__name__,
					'errors': [Error.__name__],
					'oneWay': False,
					'types': [
						convert_schema(ResponseModel),
						convert_schema(Error, error=True),
					],
				},
			},
		}
		assert ResponseModel(result=True) == model_deserializer(call_deserializer(next(frame)).response)


	def test_AvroRoute_AllAvroHeadersValidHandshakeHandshakeCached_ReturnsHandshakeAndResponse(self) :

		# arrange
		protocol = AvroProtocol(
			namespace='idk',
			protocol='idk',
			messages={
				'test_func__post': AvroMessage(
					types=[convert_schema(ResponseModel)],
					response=ResponseModel.__name__,
				),
			}
		).json()

		handshake = HandshakeRequest(
			clientHash=md5(protocol.encode()).digest(),
			serverHash=b'deadbeefdeadbeef',
			clientProtocol=protocol,
		)

		app = FastAPI()
		app.router.route_class = AvroRoute

		@app.post(endpoint, response_model=ResponseModel)
		async def test_func() :
			return ResponseModel(
				result=True,
			)

		client = TestClient(app, base_url=base_url)
		response = client.post(
			schema + base_url + endpoint,
			headers={ 'accept': 'avro/binary', 'content-type': 'avro/binary' },
			data=avro_frame(handshake_serializer(handshake)),
		)

		handshake = handshake_deserializer(next(read_avro_frames(response._content)))
		assert HandshakeMatch.client == handshake.match

		handshake = HandshakeRequest(
			clientHash=md5(protocol.encode()).digest(),
			serverHash=handshake.serverHash,
		)

		# act
		response = client.post(
			schema + base_url + endpoint,
			headers={ 'accept': 'avro/binary', 'content-type': 'avro/binary' },
			data=avro_frame(handshake_serializer(handshake)),
		)


		# assert
		frame = read_avro_frames(response._content)
		assert 200 == response.status_code
		handshake: HandshakeResponse = handshake_deserializer(next(frame))
		assert HandshakeMatch.both == handshake.match
		assert None == handshake.serverHash
		assert None == handshake.serverProtocol
		assert ResponseModel(result=True) == model_deserializer(call_deserializer(next(frame)).response)


	def test_AvroRoute_AllAvroHeadersNullResponse_ReturnsHandshakeAndResponse(self) :

		# arrange
		protocol = AvroProtocol(
			namespace='idk',
			protocol='idk',
			messages={
				'test_func__post': AvroMessage(),
			}
		).json()

		handshake = HandshakeRequest(
			clientHash=md5(protocol.encode()).digest(),
			serverHash=b'deadbeefdeadbeef',
			clientProtocol=protocol,
		)

		app = FastAPI()
		app.router.route_class = AvroRoute

		@app.post(endpoint, status_code=204)
		async def test_func() :
			assert True
			return

		client = TestClient(app, base_url=base_url)


		# act
		response = client.post(
			schema + base_url + endpoint,
			headers={ 'accept': 'avro/binary', 'content-type': 'avro/binary' },
			data=avro_frame(handshake_serializer(handshake)),
		)


		# assert
		print(response._content)
		frame = read_avro_frames(response._content)
		assert 200 == response.status_code
		handshake: HandshakeResponse = handshake_deserializer(next(frame))
		assert HandshakeMatch.client == handshake.match
		assert handshake.serverHash == md5(handshake.serverProtocol.encode()).digest()
		assert json.loads(handshake.serverProtocol) == {
			'namespace': 'kh-common',
			'protocol': 'test_func__post',
			'messages': {
				'test_func__post': {
					'doc': 'the openapi description should go here. ex: V1Endpoint',
					'request': [],
					'response': 'null',
					'errors': [Error.__name__],
					'oneWay': True,
					'types': [
						convert_schema(Error, error=True),
					],
				},
			},
		}
		assert not next(frame)


	def test_AvroRoute_AllAvroHeadersCachedNullResponse_ReturnsHandshakeAndResponse(self) :

		# arrange
		protocol = AvroProtocol(
			namespace='idk',
			protocol='idk',
			messages={
				'test_func__post': AvroMessage(),
			}
		).json()

		handshake = HandshakeRequest(
			clientHash=md5(protocol.encode()).digest(),
			serverHash=b'deadbeefdeadbeef',
			clientProtocol=protocol,
		)

		app = FastAPI()
		app.router.route_class = AvroRoute

		@app.post(endpoint, status_code=204)
		async def test_func() :
			assert True
			return

		client = TestClient(app, base_url=base_url)
		response = client.post(
			schema + base_url + endpoint,
			headers={ 'accept': 'avro/binary', 'content-type': 'avro/binary' },
			data=avro_frame(handshake_serializer(handshake)),
		)

		handshake = handshake_deserializer(next(read_avro_frames(response._content)))
		assert HandshakeMatch.client == handshake.match

		handshake = HandshakeRequest(
			clientHash=md5(protocol.encode()).digest(),
			serverHash=handshake.serverHash,
		)


		# act
		response = client.post(
			schema + base_url + endpoint,
			headers={ 'accept': 'avro/binary', 'content-type': 'avro/binary' },
			data=avro_frame(handshake_serializer(handshake)),
		)


		# assert
		print(response._content)
		frame = read_avro_frames(response._content)
		assert 200 == response.status_code
		handshake: HandshakeResponse = handshake_deserializer(next(frame))
		assert HandshakeMatch.both == handshake.match
		assert None == handshake.serverHash
		assert None == handshake.serverProtocol
		assert not next(frame)

