from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_der_public_key
from cryptography.hazmat.backends import default_backend
from kh_common.exceptions.http_error import Unauthorized
from typing import Any, Callable, Dict, Tuple, Union
from kh_common.config.constants import auth_host
from requests import post as requests_post
from kh_common.caching import ArgsCache
from kh_common.base64 import b64decode
from starlette.requests import Request
from dataclasses import dataclass
from functools import wraps
from time import time
import ujson as json


@dataclass
class TokenData :
	guid: str
	expires: int
	data: Dict[str, Any]


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
		'expires': load['expires'],
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
	guid: bytes
	data: bytes

	algorithm, key_id, expires, guid, data = load.split(b'.', 4)

	algorithm: str = algorithm.decode()
	key_id: int = int.from_bytes(b64decode(key_id), 'big')
	expires: int = int.from_bytes(b64decode(expires), 'big')
	guid: str = b64decode(guid).hex()

	if time() > expires :
		raise Unauthorized('Key has expired.')

	key: Dict[str, Union[str, int, Ed25519PublicKey]] = _fetchPublicKey(key_id, algorithm)

	if time() > key['expires'] :
		raise Unauthorized('Key has expired.')

	try :
		key['public_key'].verify(b64decode(signature), content.encode())

	except :
		raise Unauthorized('Key validation failed.')

	return TokenData(
		guid=guid,
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

	return verifyToken(token.split()[-1])


def authenticated(func: Callable) -> Callable :
	request_index: Union[int, type(None)] = None
	token_key: Union[str, type(None)] = None

	for i, (k, v) in enumerate(func.__annotations__.items()) :
		if 'req' in k.lower() :
			request_index = i
		if 'token' in k.lower() :
			token_key = k

		if issubclass(v, Request) :
			request_index = i
		if issubclass(v, TokenData) :
			token_key = k

	if request_index is None :
		raise TypeError("request object must be typed as a subclass of starlette.requests.Request or contain 'req' in its name")

	if token_key is None :
		raise TypeError("token object must be typed as a subclass of kh_common.auth.TokenData or contain 'token' in its name")

	@wraps(func)
	async def wrapper(*args: Tuple[Any], **kwargs:Dict[str, Any]) -> Any :
		request: Request = args[request_index]
		kwargs[token_key]: TokenData = retrieveTokenData(request)
		return await func(*args, **kwargs)
	return wrapper
