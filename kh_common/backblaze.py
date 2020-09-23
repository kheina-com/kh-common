from requests import Response, get as requests_get, post as requests_post
from kh_common.exceptions.base_error import BaseError
from kh_common.config.repo import name, short_hash
from kh_common.logging import getLogger, Logger
from kh_common.config.credentials import b2
from hashlib import sha1 as hashlib_sha1
from typing import Any, Dict, Union
from base64 import b64encode
from time import sleep
import ujson as json


class B2AuthorizationError(BaseError) :
	pass


class B2UploadError(BaseError) :
	pass


class B2Interface :

	def __init__(self, timeout:float=300, max_backoff:float=30, max_retries:float=15, mime_types:Dict[str, str]={ }) -> type(None) :
		self.logger: Logger = getLogger(f'{name}.{short_hash}')
		self.b2_timeout: float = timeout
		self.b2_max_backoff: float = max_backoff
		self.b2_max_retries: float = max_retries
		self.mime_types: Dict[str, str] = {
			'jpg': 'image/jpeg',
			'jpeg': 'image/jpeg',
			'png': 'image/png',
			'webp': 'image/webp',
			'gif': 'image/gif',
			'webm': 'video/webm',
			'mp4': 'video/mp4',
			'mov': 'video/quicktime',
			**mime_types,
		}
		self._b2_authorize()


	def _b2_authorize(self) -> bool :
		basic_auth_string: bytes = b'Basic ' + b64encode((b2['key_id'] + ':' + b2['key']).encode())
		b2_headers: Dict[str, bytes] = { 'Authorization': basic_auth_string }
		response: Union[Response, type(None)] = None

		for _ in range(self.b2_max_retries) :
			try :
				response = requests_get(
					'https://api.backblazeb2.com/b2api/v2/b2_authorize_account',
					headers=b2_headers,
					timeout=self.b2_timeout,
				)

			except :
				pass

			else :
				if response.ok :
					self.b2: Dict[str, Any] = json.loads(response.content)
					return True

		else :
			raise B2AuthorizationError(
				'b2 authorization handshake failed.',
				response=json.loads(response.content) if response else None,
				status=response.status_code if response else None,
			)


	def _obtain_upload_url(self) -> Dict[Any] :
		backoff: float = 1
		response: Union[Response, type(None)] = None

		for _ in range(self.b2_max_retries) :
			try :
				response = requests_post(
					self.b2['apiUrl'] + '/b2api/v2/b2_get_upload_url',
					data='{"bucketId":"' + self.b2['allowed']['bucketId'] + '"}',
					headers={ 'Authorization': self.b2['authorizationToken'] },
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
			f'Unable to obtain b2 upload url, max retries exceeded: {self.b2_max_retries}.',
			response=json.loads(response.content) if response else None,
			status=response.status_code if response else None,
		)


	def _get_mime_from_filename(self, filename: str) -> str :
		extension: str = filename[filename.rfind('.') + 1:]
		if extension in self.mime_types :
			return self.mime_types[extension.lower()]
		raise ValueError(f'file extention does not have a known mime type: {filename}')


	def b2_upload(self, file_data: bytes, filename: str, content_type:Union[str, type(None)]=None, sha1:Union[str, type(None)]=None) -> Dict[str, Any] :
		# obtain upload url
		upload_url: str = self._obtain_upload_url()

		sha1: str = sha1 or hashlib_sha1(file_data).hexdigest()
		content_type: str = content_type or self._get_mime_from_filename(filename)

		headers: Dict[str, str] = {
			'Authorization': upload_url['authorizationToken'],
			'X-Bz-File-Name': filename,
			'Content-Type': content_type,
			'Content-Length': str(len(file_data)),
			'X-Bz-Content-Sha1': sha1,
		}

		backoff: float = 1
		response: Union[Response, type(None)] = None

		for _ in range(self.b2_max_retries) :
			try :
				response = requests.post(
					upload_url['uploadUrl'],
					headers=headers,
					data=file_data,
					timeout=self.b2_timeout,
				)

			except :
				pass

			else :
				if response.ok :
					return json.loads(response.content)

			sleep(backoff)
			backoff = min(backoff * 2, self.b2_max_backoff)

		raise B2UploadError(
			f'Upload to b2 failed, max retries exceeded: {self.b2_max_retries}.',
			response=json.loads(response.content) if response else None,
			status=response.status_code if response else None,
		)
