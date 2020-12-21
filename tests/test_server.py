from kh_common.logging import LogHandler
LogHandler.logging_available = False

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from kh_common.base64 import b64encode, b64decode
from kh_common.server import Request, ServerApp
from fastapi.testclient import TestClient
from dataclasses import dataclass
from uuid import uuid4
from time import time
from math import ceil
import ujson as json


private_key = Ed25519PrivateKey.generate()
public_key = private_key.public_key().public_bytes(
	encoding=serialization.Encoding.DER,
	format=serialization.PublicFormat.SubjectPublicKeyInfo,
)
pk_signature = private_key.sign(public_key)

@dataclass
class test_response :
	text: str

endpoint = '/'
base_url = 'test.kheina.com'
schema = 'http://'
expires = int(time() + 1000)
issued = time()


class TestAppServer :

	def mock_pk(self, mocker) :
		mocker.patch('kh_common.auth.requests_post', side_effect=lambda *a, **kv : None if kv['json'] != { 'key_id': 1, 'algorithm': 'ed25519' } else test_response( text = json.dumps({
			'signature': b64encode(pk_signature).decode(),
			'key': b64encode(public_key).decode(),
			'algorithm': 'ed25519',
			'expires': expires,
			'issued': issued,
		})))


	def mock_token(self, user_id, token_data={ }) :
		load = b'.'.join([
			b'ed25519',
			b64encode((1).to_bytes(1, 'big')),
			b64encode(expires.to_bytes(ceil(expires.bit_length() / 8), 'big')),
			b64encode(user_id.to_bytes(ceil(user_id.bit_length() / 8), 'big')),
			b64encode(uuid4().bytes),
			json.dumps(token_data).encode(),
		])

		version = b'1'
		content = b64encode(version) + b'.' + b64encode(load)
		return (content + b'.' + b64encode(private_key.sign(content))).decode()


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

		@app.get(endpoint)
		async def test_func() :
			raise HttpError('test', refid='abc123')

		client = TestClient(app, base_url=base_url)

		# act
		response = client.get(schema + base_url + endpoint)

		# assert
		assert 500 == response.status_code
		assert { 'status': 500, 'refid': 'abc123', 'error': 'HttpError: test' } == response.json()


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
			req.user.VerifyAuthentication()

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
			return { 'authorized': req.user.authenticed }

		client = TestClient(app, base_url=base_url)

		# act
		response = client.get(schema + base_url + endpoint)

		# assert
		assert 200 == response.status_code
		assert { 'authorized': False } == response.json()


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
		self.mock_pk(mocker)

		app = ServerApp(auth=True, auth_required=True)

		@app.get(endpoint)
		async def test_func(req: Request) :
			return { 'user_id': req.user.user_id }

		client = TestClient(app, base_url=base_url)

		token = self.mock_token(1)

		# act
		response = client.get(schema + base_url + endpoint, headers={ 'authorization': token })

		# assert
		assert 200 == response.status_code
		assert { 'user_id': 1 } == response.json()


	def test_ServerApp_GetRequiresScope_Authorized(self, mocker) :

		# arrange
		self.mock_pk(mocker)

		app = ServerApp(auth=True, auth_required=True)

		@app.get(endpoint)
		async def test_func(req: Request) :
			return { 'user_id': req.user.user_id, 'scope': list(req.user.scope) }

		client = TestClient(app, base_url=base_url)

		token = self.mock_token(1000000, { 'scope': ['test'] })

		# act
		response = client.get(schema + base_url + endpoint, cookies={ 'kh_auth': token })

		# assert
		assert 200 == response.status_code
		response_json = response.json()
		response_json['scope'] = set(response_json['scope'])
		assert { 'user_id': 1000000, 'scope': {'user', 'test'} } == response_json
