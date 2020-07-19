from common.caching import SimpleCache
from common.HTTPError import NotFound
from common.cwd import SetCWD
try : import ujson as json
except : import json
import os

cwd = SetCWD()

@SimpleCache(900)  # 15 minute cache
def secureFolders() :
	try :
		with open('securefolders.json') as folders :
			return json.load(folders)
	except :
		return ['credentials']


def safeJoin(*args) :
	path = os.path.realpath(os.path.join(*args))
	if path.startswith(cwd) and all(folder not in path for folder in secureFolders()) and os.path.exists(path) :
		return path
	raise NotFound('The requested resource is not available.')
