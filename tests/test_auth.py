from kh_common.logging import LogHandler; LogHandler.logging_available = False
from kh_common.auth import KhAuthMiddleware, KhUser, verifyToken, Scope
from kh_common.exceptions.http_error import Forbidden, Unauthorized
from tests.utilities.auth import mock_pk, mock_token, expires
from kh_common.utilities.json import json_stream
from fastapi.testclient import TestClient
from fastapi import FastAPI, Request
from datetime import datetime
from pytest import raises
from uuid import uuid4


class TestAuthToken :

	def test_VerifyToken_ValidToken_DecodesSuccessfully(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=12345)
		user_id = 1234567890
		guid = uuid4()
		token_data = { 'ip': '127.0.0.1', 'email': 'user@example.com' }
		token = mock_token(user_id, token_data=token_data, guid=guid, key_id=12345)

		# act
		result = verifyToken(token)

		# assert
		assert user_id == result.user_id
		assert guid == result.guid
		assert datetime.fromtimestamp(expires) == result.expires
		assert token_data == result.data


	def test_VerifyToken_InvalidToken_RaisesUnauthorized(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=12345)
		user_id = 1234567890
		guid = uuid4()
		token_data = { 'ip': '127.0.0.1', 'email': 'user@example.com' }
		token = mock_token(user_id, token_data=token_data, guid=guid, key_id=12345, valid_signature=False)

		# act
		with raises(Unauthorized) :
			result = verifyToken(token)

	def test_VerifyAuthenticated_UserNotAuthenticated_RaisesUnauthorized(self) :

		# arrange
		user = KhUser(1, None, False, set([Scope.default]))

		# act
		with raises(Unauthorized) :
			result = user.VerifyAuthenticated()


	def test_VerifyAuthenticated_UserAuthenticated_ReturnsTrue(self) :

		# arrange
		user = KhUser(1, None, True, set([Scope.user]))

		# act
		result = user.VerifyAuthenticated()

		assert True == result


	def test_VerifyScope_UserNotAuthorized_RaisesForbidden(self) :

		# arrange
		user = KhUser(1, None, False, set([Scope.default]))

		# act
		with raises(Forbidden) :
			result = user.VerifyScope(Scope.user)


	def test_VerifyScope_AuthenticatedUserNotAuthorized_RaisesForbidden(self) :

		# arrange
		user = KhUser(1, None, True, set([Scope.user]))

		# act
		with raises(Forbidden) :
			result = user.VerifyScope(Scope.admin)


	def test_VerifyScope_AuthenticatedUserAuthorized_ReturnsTrue(self) :

		# arrange
		user = KhUser(1, None, True, set([Scope.admin]))

		# act
		result = user.VerifyScope(Scope.admin)

		assert True == result


class TestAuthMiddleware :

	def test_AuthMiddleware_AuthNotRequiredValidToken_200Authenticated(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=54321)
		user_id = 9876543210
		token = mock_token(user_id, key_id=54321)

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=False)

		@app.get('/')
		async def app_func(req: Request) :
			return { 'user_id': req.user.user_id, 'scope': list(req.user.scope), 'data': req.user.token.data, 'authenticated': req.user.authenticated }

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'authorization': f'bearer {token}' })

		# assert
		assert 200 == result.status_code
		assert { 'user_id': user_id, 'scope': [Scope.user], 'data': { }, 'authenticated': True } == result.json()


	def test_AuthMiddleware_AuthNotRequiredInvalidToken_200Unauthorized(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=54321)
		token = mock_token(9876543210, key_id=54321, valid_signature=False)

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=False)

		@app.get('/')
		async def app_func(req: Request) :
			return { 'user_id': req.user.user_id, 'scope': list(req.user.scope), 'token': req.user.token, 'authenticated': req.user.authenticated }

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'authorization': f'bearer {token}' })

		# assert
		assert 200 == result.status_code
		assert { 'user_id': None, 'scope': [Scope.default], 'token': None, 'authenticated': False } == result.json()


	def test_AuthMiddleware_AuthRequiredValidTokenFromHeader_200Authenticated(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=54321)
		user_id = 9876543210
		token = mock_token(user_id, key_id=54321)

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=True)

		@app.get('/')
		async def app_func(req: Request) :
			return { 'user_id': req.user.user_id, 'scope': list(req.user.scope), 'data': req.user.token.data, 'authenticated': req.user.authenticated }

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'authorization': f'bearer {token}' })

		# assert
		assert 200 == result.status_code
		assert { 'user_id': user_id, 'scope': [Scope.user], 'data': { }, 'authenticated': True } == result.json()


	def test_AuthMiddleware_AuthRequiredValidTokenFromCookie_200Authenticated(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=54321)
		user_id = 9876543210
		token = mock_token(user_id, key_id=54321)

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=True)

		@app.get('/')
		async def app_func(req: Request) :
			return { 'user_id': req.user.user_id, 'scope': list(req.user.scope), 'data': req.user.token.data, 'authenticated': req.user.authenticated }

		client = TestClient(app)

		# act
		result = client.get('/', cookies={ 'kh_auth': token })

		# assert
		assert 200 == result.status_code
		assert { 'user_id': user_id, 'scope': [Scope.user], 'data': { }, 'authenticated': True } == result.json()


	def test_AuthMiddleware_AuthRequiredInvalidTokenFromHeader_401Unauthorized(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=54321)
		user_id = 9876543210
		token = mock_token(user_id, key_id=54321, valid_signature=False)

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=True)

		@app.get('/')
		async def app_func(req: Request) :
			pass

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'authorization': f'bearer {token}' })

		# assert
		assert 401 == result.status_code
		response_json = result.json()
		assert 32 == len(response_json.pop('refid'))
		assert { 'error': 'Unauthorized: Key validation failed.', 'status': 401 } == response_json


	def test_AuthMiddleware_AuthRequiredInvalidTokenFromCookie_401Unauthorized(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=54321)
		user_id = 9876543210
		token = mock_token(user_id, key_id=54321, valid_signature=False)

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=True)

		@app.get('/')
		async def app_func(req: Request) :
			pass

		client = TestClient(app)

		# act
		result = client.get('/', cookies={ 'kh_auth': token })

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
		response_json = result.json()
		assert 32 == len(response_json.pop('refid'))
		assert { 'error': 'Unauthorized: An authentication token was not provided.', 'status': 401 } == response_json


	def test_AuthMiddleware_AuthRequiredTokenWithScopes_200Authorized(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=54321)
		user_id = 9876543210
		token = mock_token(user_id, key_id=54321, token_data={ 'scope': [ Scope.mod, Scope.admin ] })

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=True)

		@app.get('/')
		async def app_func(req: Request) :
			req.user.VerifyScope(Scope.mod)
			req.user.VerifyScope(Scope.admin)
			return json_stream({ 'user_id': req.user.user_id, 'scope': req.user.scope, 'data': req.user.token.data, 'authenticated': req.user.authenticated })

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'authorization': f'bearer {token}' })

		# assert
		assert 200 == result.status_code
		assert { 'user_id': user_id, 'scope': [Scope.user.name, Scope.mod.name, Scope.admin.name], 'data': { 'scope': [Scope.mod.name, Scope.admin.name] }, 'authenticated': True } == result.json()


	def test_AuthMiddleware_AuthRequiredTokenWithScopes_RaisesForbidden(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=54321)
		user_id = 9876543210
		token = mock_token(user_id, key_id=54321, token_data={ 'scope': [ Scope.mod ] })

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=True)

		@app.get('/')
		async def app_func(req: Request) :
			req.user.VerifyScope(Scope.mod)
			req.user.VerifyScope(Scope.admin)

		client = TestClient(app)

		# act
		with raises(Forbidden) :
			result = client.get('/', headers={ 'authorization': f'bearer {token}' })
