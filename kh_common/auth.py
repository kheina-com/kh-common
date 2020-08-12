from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from kh_common.http_error import Unauthorized
from requests import post as requests_post
from kh_common.caching import ArgsCache
from kh_common.base64 import b64decode
from time import time
import ujson as json


@ArgsCache(60 * 60 * 24)  # 24 hour cache
def fetchPublicKey(key_id, algorithm) :
	response = requests_post('http://127.0.0.1/v1/key', json={ 'key_id': key_id, 'algorithm': algorithm })
	return json.loads(response.text)


def verifyToken(token) :
	load, signature = tuple(map(b64decode, token.split('.')))
	version, algorithm, key_id, expires, guid, data = load.split(b'.', 5)

	version = version.decode()
	algorithm = algorithm.decode()
	key_id = int.from_bytes(b64decode(key_id), 'big')
	expires = int.from_bytes(b64decode(expires), 'big')
	guid = b64decode(guid).hex()

	key_data = fetchPublicKey(key_id, algorithm)

	if time() > key_data['expires'] :
		raise Unauthorized('Key has expired.')

	public_key = Ed25519PublicKey.from_public_bytes(
		b64decode(key_data['key'])
	)

	try :
		public_key.verify(signature, load)
	except :
		raise Unauthorized('Key validation failed.')

	return json.loads(data)
