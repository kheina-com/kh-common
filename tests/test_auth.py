from kh_common.logging import LogHandler; LogHandler.logging_available = False
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pytest import raises

from kh_common.auth import AuthToken, KhUser, Scope, verifyToken
from kh_common.caching.key_value_store import KeyValueStore
from kh_common.exceptions.http_error import Forbidden, Unauthorized
from kh_common.models.auth import AuthState, TokenMetadata
from tests.utilities.aerospike import AerospikeClient
from tests.utilities.auth import expires, mock_pk, mock_token


@pytest.mark.asyncio
class TestAuthToken :

	client = None

	def setup(self) :
		TestAuthToken.client = AerospikeClient()
		KeyValueStore._client = TestAuthToken.client


	async def test_VerifyToken_ValidToken_DecodesSuccessfully(self, mocker) :

		# arrange
		TestAuthToken.client.clear()
		key_id = 12345
		mock_pk(mocker, key_id=key_id)
		user_id = 1234567890
		guid = uuid4()
		token_data = { 'ip': '127.0.0.1', 'email': 'user@example.com' }
		token = mock_token(user_id, token_data=token_data, guid=guid, key_id=key_id)

		TestAuthToken.client.put(('kheina', 'token', guid.bytes), { 'data': TokenMetadata(
			state=AuthState.active,
			key_id=key_id,
			user_id=user_id,
			version=b'1',
			algorithm='ed25519',
			expires=datetime.fromtimestamp(expires, timezone.utc),
			issued=datetime.now(timezone.utc),
			fingerprint=b'',
		)})

		# act
		result = await verifyToken(token)

		# assert
		assert user_id == result.user_id
		assert guid == result.guid
		assert datetime.fromtimestamp(expires, timezone.utc) == result.expires
		assert token_data == result.data


	async def test_VerifyToken_InvalidToken_RaisesUnauthorized(self, mocker) :

		# arrange
		TestAuthToken.client.clear()
		key_id = 12345
		mock_pk(mocker, key_id=key_id)
		user_id = 1234567890
		guid = uuid4()
		token_data = { 'ip': '127.0.0.1', 'email': 'user@example.com' }
		token = mock_token(user_id, token_data=token_data, guid=guid, key_id=key_id, valid_signature=False)

		TestAuthToken.client.put(('kheina', 'token', guid.bytes), { 'data': TokenMetadata(
			state=AuthState.active,
			key_id=key_id,
			user_id=user_id,
			version=b'1',
			algorithm='ed25519',
			expires=datetime.fromtimestamp(expires, timezone.utc),
			issued=datetime.now(timezone.utc),
			fingerprint=b'',
		)})

		# act
		with raises(Unauthorized) :
			await verifyToken(token)


	async def test_VerifyToken_TamperedToken_RaisesUnauthorized(self, mocker) :

		# arrange
		TestAuthToken.client.clear()
		key_id = 12345
		mock_pk(mocker, key_id=key_id)
		user_id = 1234567890
		guid = uuid4()
		token_data = { 'ip': '127.0.0.1', 'email': 'user@example.com' }
		token_signature = mock_token(user_id, token_data=token_data, guid=guid, key_id=key_id, valid_signature=True).rsplit('.', 1)[-1]
		token_data = { 'ip': '192.168.1.1', 'email': 'user@example.com' }
		token_body = mock_token(user_id, token_data=token_data, guid=guid, key_id=key_id, valid_signature=True).rsplit('.', 1)[0]
		token = token_body + '.' + token_signature

		TestAuthToken.client.put(('kheina', 'token', guid.bytes), { 'data': TokenMetadata(
			state=AuthState.active,
			key_id=key_id,
			user_id=user_id,
			version=b'1',
			algorithm='ed25519',
			expires=datetime.fromtimestamp(expires, timezone.utc),
			issued=datetime.now(timezone.utc),
			fingerprint=b'',
		)})

		# act
		with raises(Unauthorized) :
			await verifyToken(token)


	async def test_VerifyToken_CacheTokenStateInactive_RaisesUnauthorized(self, mocker) :

		# arrange
		TestAuthToken.client.clear()
		key_id = 12345
		mock_pk(mocker, key_id=key_id)
		user_id = 1234567890
		guid = uuid4()
		token_data = { 'ip': '127.0.0.1', 'email': 'user@example.com' }
		token_signature = mock_token(user_id, token_data=token_data, guid=guid, key_id=key_id, valid_signature=True).rsplit('.', 1)[-1]
		token_data = { 'ip': '192.168.1.1', 'email': 'user@example.com' }
		token_body = mock_token(user_id, token_data=token_data, guid=guid, key_id=key_id, valid_signature=True).rsplit('.', 1)[0]
		token = token_body + '.' + token_signature

		TestAuthToken.client.put(('kheina', 'token', guid.bytes), { 'data': TokenMetadata(
			state=AuthState.inactive,
			key_id=key_id,
			user_id=user_id,
			version=b'1',
			algorithm='ed25519',
			expires=datetime.fromtimestamp(expires, timezone.utc),
			issued=datetime.now(timezone.utc),
			fingerprint=b'',
		)})

		# act
		with raises(Unauthorized) :
			await verifyToken(token)


	async def test_VerifyToken_CacheMissingTokenInfo_RaisesUnauthorized(self, mocker) :

		# arrange
		TestAuthToken.client.clear()
		key_id = 12345
		mock_pk(mocker, key_id=key_id)
		user_id = 1234567890
		guid = uuid4()
		token_data = { 'ip': '127.0.0.1', 'email': 'user@example.com' }
		token_signature = mock_token(user_id, token_data=token_data, guid=guid, key_id=key_id, valid_signature=True).rsplit('.', 1)[-1]
		token_data = { 'ip': '192.168.1.1', 'email': 'user@example.com' }
		token_body = mock_token(user_id, token_data=token_data, guid=guid, key_id=key_id, valid_signature=True).rsplit('.', 1)[0]
		token = token_body + '.' + token_signature

		# act
		with raises(Unauthorized) :
			await verifyToken(token)


	async def test_Authenticated_UserNotAuthenticated_RaisesUnauthorized(self) :

		# arrange
		TestAuthToken.client.clear()
		user = KhUser(1, None, set([Scope.default]))

		# act
		with raises(Unauthorized) :
			await user.authenticated()


	async def test_Authenticated_UserAuthenticated_ReturnsTrue(self, mocker) :

		# arrange
		TestAuthToken.client.clear()
		key_id = 123456
		mock_pk(mocker, key_id=key_id)
		user_id = 1234567890
		guid = uuid4()
		token = mock_token(user_id, guid=guid, key_id=key_id)
		user = KhUser(1, AuthToken(user_id, datetime.fromtimestamp(expires, timezone.utc), guid, {}, token), set([Scope.user]))

		TestAuthToken.client.put(('kheina', 'token', guid.bytes), { 'data': TokenMetadata(
			state=AuthState.active,
			key_id=key_id,
			user_id=user_id,
			version=b'1',
			algorithm='ed25519',
			expires=datetime.fromtimestamp(expires, timezone.utc),
			issued=datetime.now(timezone.utc),
			fingerprint=b'',
		)})

		# act
		result = await user.authenticated()

		assert True == result


	async def test_VerifyScope_UserNotAuthorized_RaisesUnauthorized(self) :

		# arrange
		TestAuthToken.client.clear()
		user = KhUser(1, None, set([Scope.default]))

		# act
		with raises(Unauthorized) :
			await user.verify_scope(Scope.user)


	async def test_VerifyScope_AuthenticatedUserNotAuthorized_RaisesForbidden(self, mocker) :

		# arrange
		TestAuthToken.client.clear()
		key_id = 123456
		mock_pk(mocker, key_id=key_id)
		user_id = 1234567890
		guid = uuid4()
		token = mock_token(user_id, guid=guid, key_id=key_id)
		user = KhUser(1, AuthToken(user_id, datetime.fromtimestamp(expires, timezone.utc), guid, {}, token), set([Scope.user]))

		TestAuthToken.client.put(('kheina', 'token', guid.bytes), { 'data': TokenMetadata(
			state=AuthState.active,
			key_id=key_id,
			user_id=user_id,
			version=b'1',
			algorithm='ed25519',
			expires=datetime.fromtimestamp(expires, timezone.utc),
			issued=datetime.now(timezone.utc),
			fingerprint=b'',
		)})

		# act
		with raises(Forbidden) :
			await user.verify_scope(Scope.admin)


	async def test_VerifyScope_AuthenticatedUserAuthorized_ReturnsTrue(self, mocker) :

		# arrange
		TestAuthToken.client.clear()
		key_id = 123456
		mock_pk(mocker, key_id=key_id)
		user_id = 1234567890
		guid = uuid4()
		token = mock_token(user_id, guid=guid, key_id=key_id)
		user = KhUser(1, AuthToken(user_id, datetime.fromtimestamp(expires, timezone.utc), guid, {}, token), set([Scope.user, Scope.admin]))

		TestAuthToken.client.put(('kheina', 'token', guid.bytes), { 'data': TokenMetadata(
			state=AuthState.active,
			key_id=key_id,
			user_id=user_id,
			version=b'1',
			algorithm='ed25519',
			expires=datetime.fromtimestamp(expires, timezone.utc),
			issued=datetime.now(timezone.utc),
			fingerprint=b'',
		)})

		# act
		result = await user.verify_scope(Scope.admin)

		assert True == result


	async def test_VerifyScope_ZeroUser_ThrowsError(self, mocker) :

		# arrange
		TestAuthToken.client.clear()
		key_id = 123456
		mock_pk(mocker, key_id=key_id)
		user_id = 0
		guid = uuid4()
		token = mock_token(user_id, guid=guid, key_id=key_id)

		# act
		with raises(Unauthorized) :
			await verifyToken(token)
