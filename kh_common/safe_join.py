from kh_common.exceptions.http_error import NotFound
from kh_common.caching import SimpleCache
from kh_common.cwd import setCwd
from typing import List, Tuple
import ujson as json
import os


cwd = setCwd()


@SimpleCache(900)  # 15 minute cache
def secureFolders() -> List[str] :
	try :
		with open('securefolders.json') as folders :
			return json.load(folders)
	except :
		return ['credentials']


def safeJoin(*args: Tuple[str]) -> str :
	path = os.path.realpath(os.path.join(*args))
	if path.startswith(cwd) and all(folder not in path for folder in secureFolders()) and os.path.exists(path) :
		return path
	raise NotFound('The requested resource is not available.')
