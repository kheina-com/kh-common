from datetime import datetime, timezone
from enum import Enum, unique
from typing import Dict
from os import environ

@unique
class Environment(Enum) :
	local: str = 'local'
	dev: str = 'dev'
	prod: str = 'prod'

	def is_local(self) :
		return self == Environment.local

	def is_dev(self) :
		return self == Environment.dev

	def is_prod(self) :
		return self == Environment.prod


environment: Environment = Environment[environ.get('ENVIRONMENT', 'LOCAL').lower()]

local: Dict[str, str] = {
	'auth_host': 'http://127.0.0.1:5000',
	'upload_host': 'http://localhost:5001',
	'tags_host': 'http://localhost:5002',
	'posts_host': 'http://localhost:5003',
	'account_host': 'http://localhost:5004',
	'users_host': 'http://localhost:5005',
	'config_host': 'http://localhost:5006',
}

dev: Dict[str, str] = {
	'auth_host': 'https://dev.kheina.com/auth',
	'upload_host': 'https://dev.kheina.com/upload',
	'tags_host': 'https://dev.kheina.com/tags',
	'posts_host': 'https://dev.kheina.com/posts',
	'account_host': 'https://dev.kheina.com/acct',
	'users_host': 'https://dev.kheina.com/users',
	'config_host': 'https://dev.kheina.com/config',
}

prod: Dict[str, str] = {
	'auth_host': 'https://auth.kheina.com',
	'upload_host': 'https://upload.kheina.com',
	'tags_host': 'https://tags.kheina.com',
	'posts_host': 'https://posts.kheina.com',
	'account_host': 'https://account.kheina.com',
	'users_host': 'https://users.kheina.com',
	'config_host': 'https://config.kheina.com',
}

assert local.keys() == dev.keys() == prod.keys()

env_vars: Dict[str, str] = locals().get(environment.name, local)

# add the variables from the environment to the module
locals().update(env_vars)

# delete extraneous data
del local, dev, prod, env_vars, environ


# put other variables/constants here (these will overwrite the env-specific configs above!)
epoch = 1576242000
