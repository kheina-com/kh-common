from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_der_public_key
from kh_common.exceptions.http_error import HttpError, Unauthorized
from starlette.types import ASGIApp, Receive, Scope, Send
from cryptography.hazmat.backends import default_backend
from typing import Any, Callable, Dict, Set, Union
from kh_common.exceptions import jsonErrorHandler
from kh_common.config.constants import auth_host
from starlette.requests import HTTPConnection
from requests import post as requests_post
from kh_common.caching import ArgsCache
from kh_common.base64 import b64decode
from fastapi import Depends, Request
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
import ujson as json


@dataclass
class TokenData :
	guid: str
	user_id: int
	expires: datetime
	data: Dict[str, Any]


@dataclass
class KhUser :

	user_id: int
	token: TokenData
	authenticed: bool
	scope: Set[str]

	def VerifyAuthentication(self) :
		if not self.authenticed :
			raise Unauthorized('User is not authenticated.')
		return True


@ArgsCache(60 * 60 * 24)  # 24 hour cache
def _fetchPublicKey(key_id: int, algorithm: str) -> Dict[str, Union[str, int]] :
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
		'expires': datetime.fromtimestamp(load['expires']),
	}


def v1token(token: str) -> TokenData :
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
	key_id: int = int.from_bytes(b64decode(key_id), 'big')
	expires: datetime = datetime.fromtimestamp(int.from_bytes(b64decode(expires), 'big'))
	user_id: int = int.from_bytes(b64decode(user_id), 'big')
	guid: str = b64decode(guid).hex()

	if datetime.now() > expires :
		raise Unauthorized('Key has expired.')

	key: Dict[str, Union[str, int, Ed25519PublicKey]] = _fetchPublicKey(key_id, algorithm)

	if datetime.now() > key['expires'] :
		raise Unauthorized('Key has expired.')

	try :
		key['public_key'].verify(b64decode(signature), content.encode())

	except :
		raise Unauthorized('Key validation failed.')

	return TokenData(
		guid=guid,
		user_id=user_id,
		expires=expires,
		data=json.loads(data),
	)


tokenVersionSwitch: Dict[bytes, Callable] = {
	b'1': v1token,
}


def verifyToken(token: str) -> TokenData :
	version: bytes = b64decode(token[:token.find('.')])

	if version in tokenVersionSwitch :
		return tokenVersionSwitch[version](token)

	raise ValueError('The given token uses a version that is unable to be decoded.')


def retrieveTokenData(request: Request) -> TokenData :
	token: str = request.headers.get('Authorization') or request.cookies.get('kh_auth')

	if not token :
		raise Unauthorized('An authentication token was not provided.')

	token_data = verifyToken(token.split()[-1])

	if 'ip' in token_data.data and token_data.data['ip'] != request.client.host :
		raise Unauthorized('The authentication token provided is not valid from this device or location.')

	return token_data


class KhAuthMiddleware:

	def __init__(self, app: ASGIApp, required: bool = True) -> type(None):
		self.app = app
		self.auth_required = required


	async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
		if scope['type'] not in {'http', 'websocket'} :
			await self.app(scope, receive, send)
			return

		request = HTTPConnection(scope)

		try :
			token_data: TokenData = retrieveTokenData(request)

			scope['user'] = KhUser(
				user_id=token_data.user_id,
				token=token_data,
				authenticed=True,
				scope={'user'} | set(token_data.data.get('scope', set())),
			)

		except HttpError as e :
			if isinstance(e, Unauthorized) and self.auth_required :
				response = jsonErrorHandler(request, e)
				await response(scope, receive, send)
				return

			scope['user'] = KhUser(
				user_id=None,
				token=None,
				authenticed=False,
				scope=set(),
			)

		await self.app(scope, receive, send)
