from kh_common.logging import LogHandler; LogHandler.logging_available = False
from kh_common.exceptions.http_error import Forbidden, Unauthorized
from kh_common.auth import AuthToken, KhUser, verifyToken, Scope
from tests.utilities.auth import mock_pk, mock_token, expires
from datetime import datetime, timezone
from pytest import raises
from uuid import uuid4
import json


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
			verifyToken(token)


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
			verifyToken(token)


	def test_Authenticated_UserNotAuthenticated_RaisesUnauthorized(self) :

		# arrange
		user = KhUser(1, None, set([Scope.default]))

		# act
		with raises(Unauthorized) :
			user.authenticated()


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


	def test_VerifyScope_UserNotAuthorized_RaisesUnauthorized(self) :

		# arrange
		user = KhUser(1, None, set([Scope.default]))

		# act
		with raises(Unauthorized) :
			user.verify_scope(Scope.user)


	def test_VerifyScope_AuthenticatedUserNotAuthorized_RaisesForbidden(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=123456)
		user_id = 1234567890
		guid = uuid4()
		token = mock_token(user_id, guid=guid, key_id=123456)
		user = KhUser(1, AuthToken(user_id, datetime.fromtimestamp(expires, timezone.utc), guid, {}, token), set([Scope.user]))

		# act
		with raises(Forbidden) :
			user.verify_scope(Scope.admin)


	def test_VerifyScope_AuthenticatedUserAuthorized_ReturnsTrue(self, mocker) :

		# arrange
		mock_pk(mocker, key_id=123456)
		user_id = 1234567890
		guid = uuid4()
		token = mock_token(user_id, guid=guid, key_id=123456)
		user = KhUser(1, AuthToken(user_id, datetime.fromtimestamp(expires, timezone.utc), guid, {}, token), set([Scope.user, Scope.admin]))

		# act
		result = user.verify_scope(Scope.admin)

		assert True == result
