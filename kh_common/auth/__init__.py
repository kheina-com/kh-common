from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_der_public_key
from kh_common.exceptions.http_error import Forbidden, Unauthorized
from typing import Any, Callable, Dict, NamedTuple, Set, Union
from cryptography.hazmat.backends import default_backend
from kh_common.models import AuthToken, KhUser, Scope
from kh_common.config.constants import auth_host
from kh_common.utilities import int_from_bytes
from requests import post as requests_post
from kh_common.caching import ArgsCache
from datetime import datetime, timezone
from kh_common.base64 import b64decode
from enum import Enum, unique
from fastapi import Request
from uuid import UUID
import ujson as json


class KhUser(KhUser) :
	def authenticated(self, raise_error=True) :
		if not self.token or self.token != verifyToken(self.token.token_string) :
			if raise_error :
				raise Unauthorized('User is not authenticated.')
			return False
		return True

	def verify_scope(self, scope: Scope) :
		self.authenticated()
		if scope not in self.scope :
			raise Forbidden('User is not authorized to access this resource.')
		return True


@ArgsCache(60 * 60 * 24)  # 24 hour cache
def _fetchPublicKey(key_id: int, algorithm: str) -> Dict[str, Union[str, int, Ed25519PublicKey]] :
	response: Response = requests_post(f'{auth_host}/v1/key', json={ 'key_id': key_id, 'algorithm': algorithm })
	load: Dict[str, Union[str, float, int]] = json.loads(response.text)

	signature: bytes = b64decode(load['signature'])
	key: bytes = b64decode(load['key'])
	public_key: Ed25519PublicKey = load_der_public_key(key, backend=default_backend())

	# don't verify in try/catch so that it doesn't cache an invalid token
	public_key.verify(signature, key)

	return {
		'key_id': key_id,
		'algorithm': algorithm,
		'public_key': public_key,
		'expires': datetime.fromtimestamp(load['expires'], timezone.utc),
	}


def v1token(token: str) -> AuthToken :
	content: str
	signature: str
	version: str
	load: str

	content, signature = token.rsplit('.', 1)
	version, load = tuple(map(b64decode, content.split('.')))

	algorithm: bytes
	key_id: bytes
	expires: bytes
	user_id: bytes
	guid: bytes
	data: bytes

	algorithm, key_id, expires, user_id, guid, data = load.split(b'.', 5)

	algorithm: str = algorithm.decode()
	key_id: int = int_from_bytes(b64decode(key_id))
	expires: datetime = datetime.fromtimestamp(int_from_bytes(b64decode(expires)), timezone.utc)
	user_id: int = int_from_bytes(b64decode(user_id))
	guid: UUID = UUID(bytes=b64decode(guid))

	if datetime.now(timezone.utc) > expires :
		raise Unauthorized('Key has expired.')

	key: Dict[str, Union[str, int, Ed25519PublicKey]] = _fetchPublicKey(key_id, algorithm)

	if datetime.now(timezone.utc) > key['expires'] :
		raise Unauthorized('Key has expired.')

	try :
		key['public_key'].verify(b64decode(signature), content.encode())

	except :
		raise Unauthorized('Key validation failed.')

	return AuthToken(
		guid=guid,
		user_id=user_id,
		expires=expires,
		data=json.loads(data),
		token_string=token,
	)


tokenVersionSwitch: Dict[bytes, Callable] = {
	b'1': v1token,
}


def verifyToken(token: str) -> AuthToken :
	version: bytes = b64decode(token[:token.find('.')])

	if version in tokenVersionSwitch :
		return tokenVersionSwitch[version](token)

	raise ValueError('The given token uses a version that is unable to be decoded.')


def retrieveAuthToken(request: Request) -> AuthToken :
	token: str = request.headers.get('Authorization') or request.cookies.get('kh-auth')

	if not token :
		raise Unauthorized('An authentication token was not provided.')

	token_data: AuthToken = verifyToken(token.split()[-1])

	# TODO: this works kind of weird with ipv6 and ephemeral ip addresses, fix later
	# if 'ip' in token_data.data and token_data.data['ip'] != request.client.host :
	# 	raise Unauthorized('The authentication token provided is not valid from this device or location.')

	return token_data
