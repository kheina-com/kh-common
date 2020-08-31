from cryptography.hazmat.primitives.serialization import load_der_public_key
from kh_common.config.constants import auth_host
from kh_common.http_error import Unauthorized
from requests import post as requests_post
from kh_common.caching import ArgsCache
from kh_common.base64 import b64decode
from time import time
import ujson as json


@ArgsCache(60 * 60 * 24)  # 24 hour cache
def _fetchPublicKey(key_id, algorithm) :
	response = requests_post(f'{auth_host}/v1/key', json={ 'key_id': key_id, 'algorithm': algorithm })
	load = json.loads(response.text)

	signature = b64decode(load['signature'])
	key = b64decode(load['key'])
	public_key = load_der_public_key(key)

	# don't verify in try/catch so that it doesn't cache an invalid token
	public_key.verify(signature, key)

	return {
		'public_key': public_key,
		'expires': load['expires'],
	}


def v1token(token) :
	content, signature = token.rsplit('.', 1)
	version, load = tuple(map(b64decode, content.split('.')))
	algorithm, key_id, expires, guid, data = load.split(b'.', 4)

	algorithm = algorithm.decode()
	key_id = int.from_bytes(b64decode(key_id), 'big')
	expires = int.from_bytes(b64decode(expires), 'big')
	guid = b64decode(guid).hex()

	if time() > expires :
		raise Unauthorized('Key has expired.')

	key = _fetchPublicKey(key_id, algorithm)

	if time() > key['expires'] :
		raise Unauthorized('Key has expired.')

	try :
		key['public_key'].verify(b64decode(signature), content.encode())
	except :
		raise Unauthorized('Key validation failed.')

	return {
		'guid': guid,
		'expires': expires,
		'data': json.loads(data),
	}


tokenVersionSwitch = {
	b'1': v1token,
}


def verifyToken(token) :
	version = b64decode(token[:token.find('.')])

	if version in tokenVersionSwitch :
		return tokenVersionSwitch[version](token)

	raise ValueError('The given token uses a version that is unable to be decoded.')
