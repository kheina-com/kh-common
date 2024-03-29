from kh_common.logging import LogHandler; LogHandler.logging_available = False
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from aiohttp import request
from fastapi import FastAPI
from fastapi.testclient import TestClient

from kh_common.auth import Scope
from kh_common.caching.key_value_store import KeyValueStore
from kh_common.config.repo import short_hash
from kh_common.models.auth import AuthState, TokenMetadata
from kh_common.server import Request, ServerApp
from kh_common.server.middleware import CustomHeaderMiddleware, HeadersToSet
from kh_common.server.middleware.cors import KhCorsMiddleware
from tests.utilities.aerospike import AerospikeClient
from tests.utilities.auth import expires, mock_pk, mock_token


endpoint = '/'
base_url = 'https://dev.fuzz.ly'


@pytest.mark.asyncio
class TestAppServer :

	client = None
	key_id = 54321
	user_id = 9876543210
	guid = uuid4()


	def setup(self) :
		TestAppServer.client = AerospikeClient()
		KeyValueStore._client = TestAppServer.client

		TestAppServer.client.put(('kheina', 'token', TestAppServer.guid.bytes), { 'data': TokenMetadata(
			state=AuthState.active,
			key_id=TestAppServer.key_id,
			user_id=TestAppServer.user_id,
			version=b'1',
			algorithm='ed25519',
			expires=datetime.fromtimestamp(expires, timezone.utc),
			issued=datetime.now(timezone.utc),
			fingerprint=b'',
		)})


	def test_ServerApp_GetNoAuth_Success(self) :

		# arrange
		app = ServerApp(auth=False)

		@app.get(endpoint)
		async def test_func() :
			return { 'result': True }

		client = TestClient(app, base_url=base_url)

		# act
		response = client.get(base_url + endpoint)

		# assert
		assert 200 == response.status_code
		assert { 'result': True } == response.json()


	def test_ServerApp_GetRaisesHttpError_CorrectErrorFormat(self) :

		# arrange
		from kh_common.exceptions.http_error import HttpError
		app = ServerApp(auth=False)
		refid = uuid4()

		@app.get(endpoint)
		async def test_func() :
			raise HttpError('test', refid=refid)

		client = TestClient(app, base_url=base_url)

		# act
		response = client.get(base_url + endpoint)

		# assert
		assert 500 == response.status_code
		assert { 'status': 500, 'refid': refid.hex, 'error': 'HttpError: test' } == response.json()


	def test_ServerApp_GetRaisesClientResponseError_CorrectErrorFormat(self) :

		# arrange
		app = ServerApp(auth=False)

		@app.get(endpoint)
		async def test_func() :
			# send request to a fake url to generate a ClientResponseError
			async with request('GET', '/') :
				pass

		client = TestClient(app, base_url=base_url)

		# act
		response = client.get(base_url + endpoint)

		# assert
		assert 502 == response.status_code
		response_json = response.json()
		assert 32 == len(response_json.pop('refid'))
		assert { 'status': 502, 'error': 'BadGateway: received an invalid response from an upstream server.' } == response_json


	def test_ServerApp_GetRaisesValueError_CorrectErrorFormat(self) :

		# arrange
		app = ServerApp(auth=False)

		@app.get(endpoint)
		async def test_func() :
			raise ValueError('test')

		client = TestClient(app, base_url=base_url)

		# act
		response = client.get(base_url + endpoint)

		# assert
		assert 500 == response.status_code
		response_json = response.json()
		assert 32 == len(response_json.pop('refid'))
		assert { 'status': 500, 'error': 'Internal Server Error' } == response_json


	def test_ServerApp_GetDoesNotRequireAuth_RaisesUnauthorized(self) :

		# arrange
		app = ServerApp(auth=True, auth_required=False)

		@app.get(endpoint)
		async def test_func(req: Request) :
			await req.user.authenticated()

		client = TestClient(app, base_url=base_url)

		# act
		response = client.get(base_url + endpoint)

		# assert
		assert 401 == response.status_code


	def test_ServerApp_GetDoesNotRequireAuth_Unauthorized(self) :

		# arrange
		app = ServerApp(auth=True, auth_required=False)

		@app.get(endpoint)
		async def test_func(req: Request) :
			return { 'authenticated': await req.user.authenticated(raise_error=False) }

		client = TestClient(app, base_url=base_url)

		# act
		response = client.get(base_url + endpoint)

		# assert
		assert 200 == response.status_code
		assert { 'authenticated': False } == response.json()


	def test_ServerApp_GetRequiresAuth_Unauthorized(self) :

		# arrange
		app = ServerApp(auth=True, auth_required=True)

		@app.get(endpoint)
		async def test_func() :
			return { 'result': True }

		client = TestClient(app, base_url=base_url)

		# act
		response = client.get(base_url + endpoint)

		# assert
		assert 401 == response.status_code


	def test_ServerApp_GetRequiresAuth_Authorized(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=TestAppServer.key_id)

		app = ServerApp(auth=True, auth_required=True)

		@app.get(endpoint)
		async def test_func(req: Request) :
			return { 'user_id': req.user.user_id }

		client = TestClient(app, base_url=base_url)

		token = mock_token(TestAppServer.user_id, key_id=TestAppServer.key_id, guid=TestAppServer.guid)

		# act
		response = client.get(base_url + endpoint, headers={ 'authorization': f'Bearer {token}' })

		# assert
		assert 200 == response.status_code
		assert { 'user_id': TestAppServer.user_id } == response.json()


	def test_ServerApp_GetRequiresScope_Authorized(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=TestAppServer.key_id)

		app = ServerApp(auth=True, auth_required=True)

		@app.get(endpoint)
		async def test_func(req: Request) :
			await req.user.verify_scope(Scope.mod)
			return { 'user_id': req.user.user_id, 'data': req.user.token.data }

		client = TestClient(app, base_url=base_url)

		token = mock_token(TestAppServer.user_id, key_id=TestAppServer.key_id, guid=TestAppServer.guid, token_data={ 'scope': [Scope.mod] })

		# act
		response = client.get(base_url + endpoint, cookies={ 'kh-auth': token })

		# assert
		assert 200 == response.status_code
		assert { 'user_id': TestAppServer.user_id, 'data': { 'scope': ['mod'] } } == response.json()


	def test_ServerApp_GetInvalidAuth_NullAuthCookie(self) :

		# arrange
		app = ServerApp(auth=True, auth_required=True)

		@app.get(endpoint)
		async def test_func() :
			return { 'result': True }

		client = TestClient(app, base_url=base_url)

		token = str(None)

		# act
		response = client.get(base_url + endpoint, cookies={ 'kh-auth': token })

		# assert
		assert 400 == response.status_code
		response_json = response.json()
		assert 32 == len(response_json.pop('refid'))
		assert { 'status': 400, 'error': 'BadRequest: The given token uses a version that is unable to be decoded.' } == response_json


	def test_ServerApp_InvalidOrigin_BadRequest(self) :

		# arrange
		app = ServerApp(auth=False, cors=True, custom_headers=False)

		@app.get(endpoint)
		async def app_func() :
			return { 'success': True }

		client = TestClient(app, base_url=base_url)

		# act
		result = client.get(f'{base_url}{endpoint}', headers={ 'Origin': 'https://example.com' })

		# assert
		assert 400 == result.status_code
		response_json = result.json()
		assert 32 == len(response_json.pop('refid'))
		assert { 'status': 400, 'error': 'BadRequest: Origin not allowed.' } == response_json


	def test_ServerApp_ValidOrigin_Success(self) :

		# arrange
		app = ServerApp(auth=False, cors=True, custom_headers=False)

		@app.get(endpoint)
		async def app_func() :
			return { 'success': True }

		client = TestClient(app, base_url=base_url)

		# act
		result = client.get(f'{base_url}{endpoint}', headers={ 'Origin': f'{base_url}' })

		# assert
		assert 200 == result.status_code
		assert { 'success': True } == result.json()


	def test_CorsMiddleware_NoOrigin_Success(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=54321)
		user_id = 9876543210
		token = mock_token(user_id, key_id=54321)

		app = FastAPI()
		app.add_middleware(KhCorsMiddleware, allowed_origins={ 'kheina.com' })

		@app.get('/')
		async def app_func(req: Request) :
			return { 'success': True }

		client = TestClient(app)

		# act
		result = client.get('/')

		# assert
		assert 200 == result.status_code
		assert { 'success': True } == result.json()


	def test_CorsMiddleware_InvalidOrigin_BadRequest(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=54321)
		user_id = 9876543210
		token = mock_token(user_id, key_id=54321)

		app = FastAPI()
		app.add_middleware(KhCorsMiddleware, allowed_origins={ 'kheina.com' })

		@app.get('/')
		async def app_func(req: Request) :
			return { 'success': True }

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'origin': 'huh' })

		# assert
		assert 400 == result.status_code
		response_json = result.json()
		assert 32 == len(response_json.pop('refid'))
		assert { 'error': 'BadRequest: Origin not allowed.', 'status': 400 } == response_json


	def test_CorsMiddleware_UnknownOrigin_BadRequest(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=54321)
		user_id = 9876543210
		token = mock_token(user_id, key_id=54321)

		app = FastAPI()
		app.add_middleware(KhCorsMiddleware, allowed_origins={ 'kheina.com' })

		@app.get('/')
		async def app_func(req: Request) :
			return { 'success': True }

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'origin': 'https://google.com' })

		# assert
		assert 400 == result.status_code
		response_json = result.json()
		assert 32 == len(response_json.pop('refid'))
		assert { 'error': 'BadRequest: Origin not allowed.', 'status': 400 } == response_json


	def test_CorsMiddleware_InvalidProtocol_BadRequest(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=54321)
		user_id = 9876543210
		token = mock_token(user_id, key_id=54321)

		app = FastAPI()
		app.add_middleware(KhCorsMiddleware, allowed_origins={ 'kheina.com' }, allowed_protocols={ 'https' })

		@app.get('/')
		async def app_func(req: Request) :
			return { 'success': True }

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'origin': 'http://kheina.com' })

		# assert
		assert 400 == result.status_code
		response_json = result.json()
		assert 32 == len(response_json.pop('refid'))
		assert { 'error': 'BadRequest: Origin not allowed.', 'status': 400 } == response_json


	def test_CorsMiddleware_ValidProtocol_Success(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=54321)
		user_id = 9876543210
		token = mock_token(user_id, key_id=54321)

		app = FastAPI()
		app.add_middleware(KhCorsMiddleware, allowed_origins={ 'kheina.com' }, allowed_protocols={ 'https' })

		@app.get('/')
		async def app_func(req: Request) :
			return { 'success': True }

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'origin': 'https://kheina.com' })

		# assert
		assert 200 == result.status_code
		assert { 'success': True } == result.json()


	def test_CustomHeaderMiddleware_HeadersInjected_Success(self) :

		# arrange
		app = ServerApp(auth=False, cors=False, custom_headers=True)

		@app.get(endpoint)
		async def app_func() :
			return { 'success': True }

		client = TestClient(app, base_url=base_url)

		# act
		result = client.get(f'{base_url}{endpoint}')

		# assert
		assert 200 == result.status_code
		assert { 'success': True } == result.json()
		assert short_hash == result.headers.get('kh-hash')


	def test_CustomHeaderMiddleware_CustomHeadersInjected_Success(self) :

		# arrange
		HeadersToSet.clear()
		HeadersToSet.update({
			'kh-hash': short_hash,
			'kh-custom': 'custom',
		})
		app = ServerApp(auth=True, auth_required=False, cors=True, custom_headers=True)

		@app.get(endpoint)
		async def app_func() :
			return { 'success': True }

		client = TestClient(app, base_url=base_url)

		# act
		result = client.get(f'{base_url}{endpoint}', headers={ 'Origin': f'{base_url}' })

		# assert
		assert 200 == result.status_code
		assert { 'success': True } == result.json()
		assert short_hash == result.headers.get('kh-hash')
		assert 'custom' == result.headers.get('kh-custom')
		assert 'kh-custom' not in result.headers.get('access-control-allow-headers', '')
		assert 'kh-custom' in result.headers.get('access-control-expose-headers', '')
