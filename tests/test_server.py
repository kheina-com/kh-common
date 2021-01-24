from kh_common.logging import LogHandler; LogHandler.logging_available = False
from kh_common.exceptions.http_error import Unauthorized
from tests.utilities.auth import mock_pk, mock_token
from kh_common.utilities.json import json_stream
from kh_common.server import Request, ServerApp
from fastapi.testclient import TestClient
from kh_common.auth import Scope
from uuid import uuid4
import ujson as json


endpoint = '/'
base_url = 'test.kheina.com'
schema = 'http://'


class TestAppServer :

	def test_ServerApp_GetNoAuth_Success(self) :

		# arrange
		app = ServerApp(auth=False)

		@app.get(endpoint)
		async def test_func() :
			return { 'result': True }

		client = TestClient(app, base_url=base_url)

		# act
		response = client.get(schema + base_url + endpoint)

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
		response = client.get(schema + base_url + endpoint)

		# assert
		assert 500 == response.status_code
		assert { 'status': 500, 'refid': refid.hex, 'error': 'HttpError: test' } == response.json()


	def test_ServerApp_GetRaisesValueError_CorrectErrorFormat(self) :

		# arrange
		app = ServerApp(auth=False)

		@app.get(endpoint)
		async def test_func() :
			raise ValueError('test')

		client = TestClient(app, base_url=base_url)

		# act
		response = client.get(schema + base_url + endpoint)

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
			req.user.authenticated()

		client = TestClient(app, base_url=base_url)

		# act
		response = client.get(schema + base_url + endpoint)

		# assert
		assert 401 == response.status_code


	def test_ServerApp_GetDoesNotRequireAuth_Unauthorized(self) :

		# arrange
		app = ServerApp(auth=True, auth_required=False)

		@app.get(endpoint)
		async def test_func(req: Request) :
			try : authenticated = req.user.authenticated()
			except Unauthorized :
				authenticated = False
			return { 'authenticated': authenticated }

		client = TestClient(app, base_url=base_url)

		# act
		response = client.get(schema + base_url + endpoint)

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
		response = client.get(schema + base_url + endpoint)

		# assert
		assert 401 == response.status_code


	def test_ServerApp_GetRequiresAuth_Authorized(self, mocker) :

		# arrange
		mock_pk(mocker)

		app = ServerApp(auth=True, auth_required=True)

		@app.get(endpoint)
		async def test_func(req: Request) :
			return { 'user_id': req.user.user_id }

		client = TestClient(app, base_url=base_url)

		token = mock_token(1)

		# act
		response = client.get(schema + base_url + endpoint, headers={ 'authorization': f'bearer {token}' })

		# assert
		assert 200 == response.status_code
		assert { 'user_id': 1 } == response.json()


	def test_ServerApp_GetRequiresScope_Authorized(self, mocker) :

		# arrange
		mock_pk(mocker)

		app = ServerApp(auth=True, auth_required=True)

		@app.get(endpoint)
		async def test_func(req: Request) :
			req.user.verify_scope(Scope.mod)
			return { 'user_id': req.user.user_id, 'data': req.user.token.data }

		client = TestClient(app, base_url=base_url)

		token = mock_token(1000000, { 'scope': [Scope.mod] })

		# act
		response = client.get(schema + base_url + endpoint, cookies={ 'kh_auth': token })

		# assert
		assert 200 == response.status_code
		response_json = response.json()
		assert { 'user_id': 1000000, 'data': { 'scope': ['mod'] } } == response_json
