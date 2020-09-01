from kh_common.exceptions.base_error import BaseError
from kh_common.config.credentials import b2
from hashlib import sha1 as hashlib_sha1
from kh_common.logging import getLogger
from base64 import b64encode
from time import sleep
import ujson as json
import requests


class B2AuthorizationError(BaseError) :
	pass


class B2UploadError(BaseError) :
	pass


class B2Interface :

	def __init__(self, timeout=300, max_backoff=30, max_retries=15, mime_types={ }) :
		self.logger = getLogger('b2-interface')
		self.b2_timeout = timeout
		self.b2_max_backoff = max_backoff
		self.b2_max_retries = max_retries
		self.mime_types = {
			'image/jpeg': 'jpg',
			'image/png': 'png',
			'image/webp': 'webp',
			'image/gif': 'gif',
			'video/webm': 'webm',
			'video/mp4': 'mp4',
			'video/quicktime': 'mov',
			**mime_types,
		}


	def authorize_b2(self) :
		basic_auth_string = b'Basic ' + b64encode((b2['key_id'] + ':' + B2['key']).encode())
		b2_headers = { 'Authorization': basic_auth_string }
		response = requests.get(
			'https://api.backblazeb2.com/b2api/v2/b2_authorize_account',
			headers=b2_headers,
			timeout=self.b2_timeout,
		)

		if response.ok :
			self.B2 = json.loads(response.content)
			return True

		else :
			raise B2AuthorizationError('B2 authorization handshake failed.', response=response.content)


	def _obtain_upload_url(self) :
		backoff = 1
		response = None
		for _ in range(self.b2_max_retries) :
			try :
				response = requests.post(
					self.B2['apiUrl'] + '/b2api/v2/b2_get_upload_url',
					data='{"bucketId":"' + self.B2['allowed']['bucketId'] + '"}',
					headers={ 'Authorization': self.B2['authorizationToken'] },
					timeout=self.b2_timeout,
				)

			except :
				pass

			else :
				if response.ok :
					return json.loads(response.content)

				elif response.status_code == 401 :
					# obtain new auth token
					self.authorize_b2()

			sleep(backoff)
			backoff = min(backoff * 2, self.b2_max_backoff)

		raise B2AuthorizationError(
			f'Unable to obtain B2 upload url, max retries exceeded: {self.b2_max_retries}.',
			response=json.loads(response.content) if response else None,
			status=response.status_code if response else None,
		)


	def b2_upload(self, file_data, content_type, filename=None, sha1=None, extension=None) :
		# obtain upload url
		upload_url = self._obtain_upload_url()

		sha1  = sha1 or hashlib_sha1(file_data).hexdigest()
		extension = extension or self.mime_types[content_type]
		filename = filename or f'{sha1}.{extension}'

		headers = {
			'Authorization': upload_url['authorizationToken'],
			'X-Bz-File-Name': filename,
			'Content-Type': content_type,
			'Content-Length': str(len(filedata)),
			'X-Bz-Content-Sha1': sha1,
		}

		backoff = 1
		for _ in range(self.b2_max_retries) :
			try :
				response = requests.post(
					upload_url['uploadUrl'],
					headers=headers,
					data=filedata,
					timeout=self.imageTimeout,
				)

			except :
				pass

			else :
				if response.ok : return json.loads(response.content)

			sleep(backoff)
			backoff = min(backoff * 2, self.b2_max_backoff)

		raise B2UploadError(f'Upload to B2 failed, max retries exceeded: {self.b2_max_retries}.')
