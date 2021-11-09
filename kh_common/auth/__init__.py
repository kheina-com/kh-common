from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from kh_common.models.auth import AuthToken, KhUser, PublicKeyResponse, Scope
from cryptography.hazmat.primitives.serialization import load_der_public_key
from kh_common.exceptions.http_error import Forbidden, Unauthorized
from cryptography.hazmat.backends import default_backend
from kh_common.base64 import b64decode, b64encode
from kh_common.config.constants import auth_host
from kh_common.utilities import int_from_bytes
from aiohttp import request as async_request
from typing import Callable, Dict, Union
from kh_common.datetime import datetime
from kh_common.caching import ArgsCache
from fastapi import Request
from hashlib import sha1
from uuid import UUID
import ujson as json
from re import compile as re_compile


ua_strip = re_compile(r'\/\d+(?:\.\d+)*')


class InvalidToken(ValueError) :
	pass


class KhUser(KhUser) :
	async def authenticated(self, raise_error=True) :
		if not self.token or self.token != await verifyToken(self.token.token_string) :
			if raise_error :
				raise Unauthorized('User is not authenticated.')
			return False
		return True

	async def verify_scope(self, scope: Scope) :
		await self.authenticated()
		if scope not in self.scope :
			raise Forbidden('User is not authorized to access this resource.')
		return True


@ArgsCache(60 * 60 * 24)  # 24 hour cache
async def _fetchPublicKey(key_id: int, algorithm: str) -> Ed25519PublicKey :
	async with async_request(
		'POST',
		f'{auth_host}/v1/key',
		json={
			'key_id': key_id,
			'algorithm': algorithm,
		},
		raise_for_status=True,
	) as response :
		load: PublicKeyResponse = PublicKeyResponse.parse_obj(await response.json())

	if datetime.now() > datetime.fromtimestamp(load.expires) :
		raise Unauthorized('Key has expired.')

	key: bytes = b64decode(load.key)
	public_key: Ed25519PublicKey = load_der_public_key(key, backend=default_backend())

	# don't verify in try/catch so that it doesn't cache an invalid token
	public_key.verify(b64decode(load.signature), key)

	return public_key


async def v1token(token: str) -> AuthToken :
	content: str
	signature: str
	load: str

	content, signature = token.rsplit('.', 1)
	load = b64decode(content[content.find('.')+1:])

	algorithm: bytes
	key_id: bytes
	expires: bytes
	user_id: bytes
	guid: bytes
	data: bytes

	algorithm, key_id, expires, user_id, guid, data = load.split(b'.', 5)

	algorithm: str = algorithm.decode()
	key_id: int = int_from_bytes(b64decode(key_id))
	expires: datetime = datetime.fromtimestamp(int_from_bytes(b64decode(expires)))
	user_id: int = int_from_bytes(b64decode(user_id))
	guid: UUID = UUID(bytes=b64decode(guid))

	if datetime.now() > expires :
		raise Unauthorized('Key has expired.')

	public_key: Dict[str, Union[str, int, Ed25519PublicKey]] = await _fetchPublicKey(key_id, algorithm)

	try :
		public_key.verify(b64decode(signature), content.encode())

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


async def verifyToken(token: str) -> AuthToken :
	version: bytes = b64decode(token[:token.find('.')])

	if version in tokenVersionSwitch :
		return await tokenVersionSwitch[version](token)

	raise InvalidToken('The given token uses a version that is unable to be decoded.')


async def retrieveAuthToken(request: Request) -> AuthToken :
	token: str = request.headers.get('Authorization') or request.cookies.get('kh-auth')

	if not token :
		raise Unauthorized('An authentication token was not provided.')

	token_data: AuthToken = await verifyToken(token.split()[-1])

	# TODO: this works great, but needs to be shelved until internal authentication is done
	# if 'fp' in token_data.data and token_data.data['fp'] != browserFingerprint(request) :
	# 	raise Unauthorized('The authentication token provided is not valid from this device or location.')

	return token_data


def browserFingerprint(request: Request) -> str :
	headers = json.dumps({
		'user-agent': userAgentStrip(request.headers.get('user-agent')),
		'connection': request.headers.get('connection'),
		'host': request.headers.get('host'),
		'accept-language': request.headers.get('accept-language'),
		'dnt': request.headers.get('dnt'),
		# "sec-fetch-dest": "empty",
		# "sec-fetch-mode": "cors",
		# "sec-fetch-site": "same-origin",
		'pragma': request.headers.get('pragma'),
		'cache-control': request.headers.get('cache-control'),
		'cdn-loop': request.headers.get('cdn-loop'),
		'cf-ipcountry': request.headers.get('cf-ipcountry'),
		'ip': request.headers.get('cf-connecting-ip') or request.client.host,
	})

	return b64encode(sha1(headers.encode()).digest()).decode()


def userAgentStrip(ua: str) :
	if not ua :
		return None
	parts = ua.partition('/')
	return ''.join(parts[:-1] + (ua_strip.sub('', parts[-1]),))
