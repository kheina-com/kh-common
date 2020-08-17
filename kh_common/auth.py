from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from kh_common.config.constants import auth_host
from kh_common.http_error import Unauthorized
from requests import post as requests_post
from kh_common.caching import ArgsCache
from kh_common.base64 import b64decode
from time import time
import ujson as json


@ArgsCache(60 * 60 * 24)  # 24 hour cache
def fetchPublicKey(key_id, algorithm) :
	response = requests_post(f'{auth_host}/v1/key', json={ 'key_id': key_id, 'algorithm': algorithm })
	return json.loads(response.text)


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

	key_data = fetchPublicKey(key_id, algorithm)

	if time() > key_data['expires'] :
		raise Unauthorized('Key has expired.')

	public_key = Ed25519PublicKey.from_public_bytes(
		b64decode(key_data['key'])
	)

	try :
		public_key.verify(b64decode(signature), content.encode())
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