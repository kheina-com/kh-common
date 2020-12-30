from kh_common.logging import LogHandler; LogHandler.logging_available = False
from kh_common.auth import AuthToken, KhAuthMiddleware, KhUser, verifyToken, Scope
from kh_common.exceptions.http_error import Forbidden, Unauthorized
from tests.utilities.auth import mock_pk, mock_token, expires
from kh_common.utilities.json import json_stream
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from fastapi import FastAPI, Request
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
		assert datetime.fromtimestamp(expires, timezone.utc) == result.expires
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


	def test_VerifyToken_TamperedToken_RaisesUnauthorized(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=12345)
		user_id = 1234567890
		guid = uuid4()
		token_data = { 'ip': '127.0.0.1', 'email': 'user@example.com' }
		token_signature = mock_token(user_id, token_data=token_data, guid=guid, key_id=12345, valid_signature=True).rsplit('.', 1)[-1]
		token_data = { 'ip': '192.168.1.1', 'email': 'user@example.com' }
		token_body = mock_token(user_id, token_data=token_data, guid=guid, key_id=12345, valid_signature=True).rsplit('.', 1)[0]
		token = token_body + '.' + token_signature

		# act
		with raises(Unauthorized) :
			result = verifyToken(token)


	def test_Authenticated_UserNotAuthenticated_RaisesUnauthorized(self) :

		# arrange
		user = KhUser(1, None, set([Scope.default]))

		# act
		with raises(Unauthorized) :
			result = user.authenticated()


	def test_Authenticated_UserAuthenticated_ReturnsTrue(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=123456)
		user_id = 1234567890
		guid = uuid4()
		token = mock_token(user_id, guid=guid, key_id=123456)
		user = KhUser(1, AuthToken(user_id, datetime.fromtimestamp(expires, timezone.utc), guid, {}, token), set([Scope.user]))

		# act
		result = user.authenticated()

		assert True == result


	def test_VerifyScope_UserNotAuthorized_RaisesForbidden(self) :

		# arrange
		user = KhUser(1, None, set([Scope.default]))

		# act
		with raises(Forbidden) :
			result = user.verify_scope(Scope.user)


	def test_VerifyScope_AuthenticatedUserNotAuthorized_RaisesForbidden(self) :

		# arrange
		user = KhUser(1, None, set([Scope.user]))

		# act
		with raises(Forbidden) :
			result = user.verify_scope(Scope.admin)


	def test_VerifyScope_AuthenticatedUserAuthorized_ReturnsTrue(self) :

		# arrange
		user = KhUser(1, None, set([Scope.admin]))

		# act
		result = user.verify_scope(Scope.admin)

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
			return json_stream({ 'user_id': req.user.user_id, 'scope': req.user.scope, 'data': req.user.token.data, 'authenticated': req.user.authenticated() })

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'authorization': f'bearer {token}' })

		# assert
		assert 200 == result.status_code
		assert { 'user_id': user_id, 'scope': [Scope.user.name], 'data': { }, 'authenticated': True } == result.json()


	def test_AuthMiddleware_AuthNotRequiredInvalidToken_200Unauthorized(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=54321)
		token = mock_token(9876543210, key_id=54321, valid_signature=False)

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=False)

		@app.get('/')
		async def app_func(req: Request) :
			try : authenticated = req.user.authenticated()
			except Unauthorized :
				authenticated = False
			return json_stream({ 'user_id': req.user.user_id, 'scope': req.user.scope, 'token': req.user.token, 'authenticated': authenticated })

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'authorization': f'bearer {token}' })

		# assert
		assert 200 == result.status_code
		assert { 'user_id': None, 'scope': [Scope.default.name], 'token': None, 'authenticated': False } == result.json()


	def test_AuthMiddleware_AuthRequiredValidTokenFromHeader_200Authenticated(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=54321)
		user_id = 9876543210
		token = mock_token(user_id, key_id=54321)

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=True)

		@app.get('/')
		async def app_func(req: Request) :
			return json_stream({ 'user_id': req.user.user_id, 'scope': req.user.scope, 'data': req.user.token.data, 'authenticated': req.user.authenticated() })

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'authorization': f'bearer {token}' })

		# assert
		assert 200 == result.status_code
		assert { 'user_id': user_id, 'scope': [Scope.user.name], 'data': { }, 'authenticated': True } == result.json()


	def test_AuthMiddleware_AuthRequiredValidTokenFromCookie_200Authenticated(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=54321)
		user_id = 9876543210
		token = mock_token(user_id, key_id=54321)

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=True)

		@app.get('/')
		async def app_func(req: Request) :
			return json_stream({ 'user_id': req.user.user_id, 'scope': req.user.scope, 'data': req.user.token.data, 'authenticated': req.user.authenticated() })

		client = TestClient(app)

		# act
		result = client.get('/', cookies={ 'kh_auth': token })

		# assert
		assert 200 == result.status_code
		assert { 'user_id': user_id, 'scope': [Scope.user.name], 'data': { }, 'authenticated': True } == result.json()


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
		result_json = result.json()
		assert 32 == len(result_json.pop('refid'))
		assert { 'error': 'Unauthorized: An authentication token was not provided.', 'status': 401 } == result_json


	def test_AuthMiddleware_AuthRequiredTokenWithScopes_200Authorized(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=54321)
		user_id = 9876543210
		token = mock_token(user_id, key_id=54321, token_data={ 'scope': [ Scope.mod, Scope.admin ] })

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=True)

		@app.get('/')
		async def app_func(req: Request) :
			req.user.verify_scope(Scope.mod)
			req.user.verify_scope(Scope.admin)
			return json_stream({ 'user_id': req.user.user_id, 'scope': req.user.scope, 'data': req.user.token.data, 'authenticated': req.user.authenticated() })

		client = TestClient(app)

		# act
		result = client.get('/', headers={ 'authorization': f'bearer {token}' })

		# assert
		assert 200 == result.status_code
		result_json = result.json()
		result_json['scope'] = set(result_json['scope'])
		assert { 'user_id': user_id, 'scope': {Scope.user.name, Scope.mod.name, Scope.admin.name}, 'data': { 'scope': [Scope.mod.name, Scope.admin.name] }, 'authenticated': True } == result_json


	def test_AuthMiddleware_AuthRequiredTokenWithScopes_RaisesForbidden(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=54321)
		user_id = 9876543210
		token = mock_token(user_id, key_id=54321, token_data={ 'scope': [ Scope.mod ] })

		app = FastAPI()
		app.add_middleware(KhAuthMiddleware, required=True)

		@app.get('/')
		async def app_func(req: Request) :
			req.user.verify_scope(Scope.mod)
			req.user.verify_scope(Scope.admin)

		client = TestClient(app)

		# act
		with raises(Forbidden) :
			result = client.get('/', headers={ 'authorization': f'bearer {token}' })
