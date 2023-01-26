from datetime import datetime, timezone
from enum import Enum, unique
from os import environ
from typing import Dict


@unique
class Environment(Enum) :
	local: str = 'local'
	dev: str = 'dev'
	prod: str = 'prod'
	test: str = 'test'

	def is_local(self) :
		return self == Environment.local

	def is_dev(self) :
		return self == Environment.dev

	def is_prod(self) :
		return self == Environment.prod

	def is_test(self) :
		return self == Environment.test


environment: Environment = Environment[environ.get('ENVIRONMENT', 'LOCAL').lower()]

test: Dict[str, str] = {
	'auth_host': 'http://127.0.0.1:5000',
	'upload_host': 'http://localhost:5001',
	'tags_host': 'http://localhost:5002',
	'posts_host': 'http://localhost:5003',
	'account_host': 'http://localhost:5004',
	'users_host': 'http://localhost:5005',
	'config_host': 'http://localhost:5006',
	'avro_host': 'http://localhost:5007',
}

local: Dict[str, str] = {
	'auth_host': 'http://127.0.0.1:5000',
	'upload_host': 'http://localhost:5001',
	'tags_host': 'http://localhost:5002',
	'posts_host': 'http://localhost:5003',
	'account_host': 'http://localhost:5004',
	'users_host': 'http://localhost:5005',
	'config_host': 'http://localhost:5006',
	'avro_host': 'http://localhost:5007',
}

dev: Dict[str, str] = {
	'auth_host': 'https://auth-dev.fuzz.ly',
	'upload_host': 'https://upload-dev.fuzz.ly',
	'tags_host': 'https://tags-dev.fuzz.ly',
	'posts_host': 'https://posts-dev.fuzz.ly',
	'account_host': 'https://account-dev.fuzz.ly',
	'users_host': 'https://users-dev.fuzz.ly',
	'config_host': 'https://config-dev.fuzz.ly',
	'avro_host': 'https://avro-dev.fuzz.ly',
}

prod: Dict[str, str] = {
	'auth_host': 'https://auth.fuzz.ly',
	'upload_host': 'https://upload.fuzz.ly',
	'tags_host': 'https://tags.fuzz.ly',
	'posts_host': 'https://posts.fuzz.ly',
	'account_host': 'https://account.fuzz.ly',
	'users_host': 'https://users.fuzz.ly',
	'config_host': 'https://config.fuzz.ly',
	'avro_host': 'https://avro.fuzz.ly',
}

assert test.keys() == local.keys() == dev.keys() == prod.keys()

env_vars: Dict[str, str] = locals().get(environment.name, local)

# add the variables from the environment to the module
locals().update(env_vars)

# delete extraneous data
del local, dev, prod, env_vars, environ


# put other variables/constants here (these will overwrite the env-specific configs above!)
epoch = 1576242000
