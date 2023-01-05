from kh_common.logging import LogHandler; LogHandler.logging_available = False
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pytest import raises

from kh_common.auth import Scope
from kh_common.caching.key_value_store import KeyValueStore
from kh_common.config.repo import short_hash
from kh_common.exceptions.http_error import BadRequest, Forbidden, Unauthorized
from kh_common.models.auth import AuthState, TokenMetadata
from kh_common.server.middleware import CustomHeaderMiddleware, HeadersToSet
from kh_common.server.middleware.auth import KhAuthMiddleware
from kh_common.server.middleware.cors import KhCorsMiddleware
from kh_common.utilities.json import json_stream
from tests.utilities.aerospike import AerospikeClient
from tests.utilities.auth import expires, mock_pk, mock_token


@pytest.mark.asyncio
class TestAuthMiddleware :

	client = None
	key_id = 54321
	user_id = 9876543210
	guid = uuid4()


	def setup(self) :
		TestAuthMiddleware.client = AerospikeClient()
		KeyValueStore._client = TestAuthMiddleware.client

		TestAuthMiddleware.client.put(('kheina', 'token', TestAuthMiddleware.guid.bytes), { 'data': TokenMetadata(
			state=AuthState.active,
			key_id=TestAuthMiddleware.key_id,
			user_id=TestAuthMiddleware.user_id,
			version=b'1',
			algorithm='ed25519',
			expires=datetime.fromtimestamp(expires, timezone.utc),
			issued=datetime.now(timezone.utc),
			fingerprint=b'',
		)})


	def test_AuthMiddleware_AuthNotRequiredValidToken_200Authenticated(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=TestAuthMiddleware.key_id)
		token = mock_token(TestAuthMiddleware.user_id, key_id=TestAuthMiddleware.key_id, guid=TestAuthMiddleware.guid)

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=False)

		@app.get('/')
		async def app_func(req: Request) :
			return json_stream({ 'user_id': req.user.user_id, 'scope': req.user.scope, 'data': req.user.token.data, 'authenticated': await req.user.authenticated() })

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'authorization': f'Bearer {token}' })

		# assert
		assert 200 == result.status_code
		assert { 'user_id': TestAuthMiddleware.user_id, 'scope': [Scope.user.name], 'data': { }, 'authenticated': True } == result.json()


	def test_AuthMiddleware_AuthNotRequiredInvalidToken_200Unauthorized(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=TestAuthMiddleware.key_id)
		token = mock_token(TestAuthMiddleware.user_id, key_id=TestAuthMiddleware.key_id, guid=TestAuthMiddleware.guid, valid_signature=False)

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=False)

		@app.get('/')
		async def app_func(req: Request) :
			return json_stream({ 'user_id': req.user.user_id, 'scope': req.user.scope, 'token': req.user.token, 'authenticated': await req.user.authenticated(raise_error=False) })

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'authorization': f'Bearer {token}' })

		# assert
		assert 200 == result.status_code
		assert { 'user_id': None, 'scope': [Scope.default.name], 'token': None, 'authenticated': False } == result.json()


	def test_AuthMiddleware_AuthRequiredValidTokenFromHeader_200Authenticated(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=TestAuthMiddleware.key_id)
		token = mock_token(TestAuthMiddleware.user_id, key_id=TestAuthMiddleware.key_id, guid=TestAuthMiddleware.guid)

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=True)

		@app.get('/')
		async def app_func(req: Request) :
			return json_stream({ 'user_id': req.user.user_id, 'scope': req.user.scope, 'data': req.user.token.data, 'authenticated': await req.user.authenticated() })

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'authorization': f'Bearer {token}' })

		# assert
		assert 200 == result.status_code
		assert { 'user_id': TestAuthMiddleware.user_id, 'scope': [Scope.user.name], 'data': { }, 'authenticated': True } == result.json()


	def test_AuthMiddleware_AuthRequiredValidTokenFromCookie_200Authenticated(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=TestAuthMiddleware.key_id)
		token = mock_token(TestAuthMiddleware.user_id, key_id=TestAuthMiddleware.key_id, guid=TestAuthMiddleware.guid)

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=True)

		@app.get('/')
		async def app_func(req: Request) :
			return json_stream({ 'user_id': req.user.user_id, 'scope': req.user.scope, 'data': req.user.token.data, 'authenticated': await req.user.authenticated() })

		client = TestClient(app)

		# act
		result = client.get('/', cookies={ 'kh-auth': token })

		# assert
		assert 200 == result.status_code
		assert { 'user_id': TestAuthMiddleware.user_id, 'scope': [Scope.user.name], 'data': { }, 'authenticated': True } == result.json()


	def test_AuthMiddleware_AuthRequiredInvalidTokenFromHeader_401Unauthorized(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=TestAuthMiddleware.key_id)
		token = mock_token(TestAuthMiddleware.user_id, key_id=TestAuthMiddleware.key_id, guid=TestAuthMiddleware.guid, valid_signature=False)

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=True)

		@app.get('/')
		async def app_func(req: Request) :
			pass

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'authorization': f'Bearer {token}' })

		# assert
		assert 401 == result.status_code
		response_json = result.json()
		assert 32 == len(response_json.pop('refid'))
		assert { 'error': 'Unauthorized: Key validation failed.', 'status': 401 } == response_json


	def test_AuthMiddleware_AuthRequiredInvalidTokenFromCookie_401Unauthorized(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=TestAuthMiddleware.key_id)
		token = mock_token(TestAuthMiddleware.user_id, key_id=TestAuthMiddleware.key_id, guid=TestAuthMiddleware.guid, valid_signature=False)

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=True)

		@app.get('/')
		async def app_func(req: Request) :
			pass

		client = TestClient(app)

		# act
		result = client.get('/', cookies={ 'kh-auth': token })

		# assert
		assert 401 == result.status_code
		response_json = result.json()
		assert 32 == len(response_json.pop('refid'))
		assert { 'error': 'Unauthorized: Key validation failed.', 'status': 401 } == response_json


	def test_AuthMiddleware_AuthRequiredNoToken_401Unauthorized(self, mocker) :

		# arrange
		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=True)

		@app.get('/')
		async def app_func(req: Request) :
			pass

		client = TestClient(app)

		# act
		result = client.get('/')

		# assert
		assert 401 == result.status_code
		result_json = result.json()
		assert 32 == len(result_json.pop('refid'))
		assert { 'error': 'Unauthorized: An authentication token was not provided.', 'status': 401 } == result_json


	def test_AuthMiddleware_AuthRequiredTokenWithScopes_200Authorized(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=TestAuthMiddleware.key_id)
		token = mock_token(TestAuthMiddleware.user_id, key_id=TestAuthMiddleware.key_id, guid=TestAuthMiddleware.guid, token_data={ 'scope': [ Scope.mod, Scope.admin ] })

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=True)

		@app.get('/')
		async def app_func(req: Request) :
			await req.user.verify_scope(Scope.mod)
			await req.user.verify_scope(Scope.admin)
			return json_stream({ 'user_id': req.user.user_id, 'scope': req.user.scope, 'data': req.user.token.data, 'authenticated': await req.user.authenticated() })

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'authorization': f'Bearer {token}' })

		# assert
		assert 200 == result.status_code
		result_json = result.json()
		result_json['scope'] = set(result_json['scope'])
		assert { 'user_id': TestAuthMiddleware.user_id, 'scope': {Scope.user.name, Scope.mod.name, Scope.admin.name}, 'data': { 'scope': [Scope.mod.name, Scope.admin.name] }, 'authenticated': True } == result_json


	def test_AuthMiddleware_AuthRequiredTokenWithScopes_RaisesForbidden(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=TestAuthMiddleware.key_id)
		token = mock_token(TestAuthMiddleware.user_id, key_id=TestAuthMiddleware.key_id, guid=TestAuthMiddleware.guid, token_data={ 'scope': [ Scope.mod ] })

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=True)

		@app.get('/')
		async def app_func(req: Request) :
			await req.user.verify_scope(Scope.mod)
			await req.user.verify_scope(Scope.admin)

		client = TestClient(app)

		# act
		with raises(Forbidden) :
			client.get('/', headers={ 'authorization': f'Bearer {token}' })


class TestCorsMiddleware :

	CorsHeaders = {
		'access-control-allow-origin',
		'access-control-allow-methods',
		'access-control-allow-headers',
		'access-control-allow-credentials',
		'access-control-max-age',
		'access-control-expose-headers',
	}

	def test_CorsMiddleware_ValidOrigin_Success(self) :

		# arrange
		app = FastAPI()
		app.add_middleware(KhCorsMiddleware, allowed_origins={ 'kheina.com' })

		@app.get('/')
		async def app_func(req: Request) :
			return { 'success': True }

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'origin': 'https://kheina.com' })

		# assert
		assert 200 == result.status_code
		assert { 'success': True } == result.json()
		assert self.CorsHeaders.issubset(result.headers.keys())


	def test_CorsMiddleware_NoOrigin_Success(self) :

		# arrange
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
		assert not (self.CorsHeaders & result.headers.keys())


	def test_CorsMiddleware_InvalidOrigin_BadRequest(self) :

		# arrange
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
		assert not (self.CorsHeaders & result.headers.keys())


	def test_CorsMiddleware_UnknownOrigin_BadRequest(self) :

		# arrange
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
		assert not (self.CorsHeaders & result.headers.keys())


	def test_CorsMiddleware_InvalidProtocol_BadRequest(self) :

		# arrange
		app = FastAPI()
		app.add_middleware(KhCorsMiddleware, allowed_origins={ 'kheina.com' }, allowed_protocols={ 'http' })

		@app.get('/')
		async def app_func(req: Request) :
			return { 'success': True }

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'origin': 'https://kheina.com' })

		# assert
		assert 400 == result.status_code
		response_json = result.json()
		assert 32 == len(response_json.pop('refid'))
		assert { 'error': 'BadRequest: Origin not allowed.', 'status': 400 } == response_json
		assert not (self.CorsHeaders & result.headers.keys())


	def test_CorsMiddleware_ValidProtocol_Success(self) :

		# arrange
		app = FastAPI()
		app.add_middleware(KhCorsMiddleware, allowed_origins={ 'kheina.com' }, allowed_protocols={ 'http' })

		@app.get('/')
		async def app_func(req: Request) :
			return { 'success': True }

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'origin': 'http://kheina.com' })

		# assert
		assert 200 == result.status_code
		assert { 'success': True } == result.json()
		assert self.CorsHeaders.issubset(result.headers.keys())


	def test_CorsMiddleware_InvalidProtocol_BadRequest(self) :

		# arrange
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
		assert not (self.CorsHeaders & result.headers.keys())


	def test_CorsMiddleware_ValidRequest_HeadersAccurate(self) :

		# arrange
		app = FastAPI()
		app.add_middleware(
			KhCorsMiddleware,
			allowed_origins=['dev.kheina.com', 'localhost'],
			allowed_protocols=['https'],
			allowed_methods=['delete', 'post', 'eggs'],
			allowed_headers=['biscuit'],
			allow_credentials=False,
			max_age=123456,
		)

		@app.get('/')
		async def app_func(req: Request) :
			return { 'success': True }

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'origin': 'https://localhost' })

		# assert
		assert 200 == result.status_code
		assert { 'success': True } == result.json()
		assert 'https://localhost' == result.headers['access-control-allow-origin']
		assert 'DELETE, POST, EGGS' == result.headers['access-control-allow-methods']
		assert 'biscuit' in result.headers['access-control-allow-headers']
		assert '123456' == result.headers['access-control-max-age']
		assert 'false' == result.headers['access-control-allow-credentials']


class TestCustomHeadersMiddleware :

	def test_CustomHeadersMiddleware_ValidRequest_HeadersAccurate(self) :

		# arrange
		app = FastAPI()
		app.middleware('http')(CustomHeaderMiddleware)

		@app.get('/')
		async def app_func(req: Request) :
			return { 'success': True }

		client = TestClient(app)

		# act
		result = client.get('/')

		# assert
		assert 200 == result.status_code
		assert { 'success': True } == result.json()
		assert short_hash == result.headers['kh-hash']


	def test_CustomHeadersMiddleware_HeadersChanged_HeadersAccurate(self) :

		# arrange
		app = FastAPI()
		app.middleware('http')(CustomHeaderMiddleware)
		HeadersToSet.clear()
		HeadersToSet.update({
			'kh-hash': short_hash,
			'kh-custom': 'custom',
		})

		@app.get('/')
		async def app_func(req: Request) :
			return { 'success': True }

		client = TestClient(app)

		# act
		result = client.get('/')

		# assert
		assert 200 == result.status_code
		assert { 'success': True } == result.json()
		assert short_hash == result.headers.get('kh-hash')
		assert 'custom' == result.headers.get('kh-custom')
