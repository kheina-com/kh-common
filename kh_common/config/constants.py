from typing import Dict
from os import environ


environment: str = environ.get('ENVIRONMENT', 'LOCAL').lower()

local: Dict[str, str] = {
	'auth_host': 'http://127.0.0.1:5000',
}

dev: Dict[str, str] = {
	'auth_host': 'https://auth-dev.kheina.com',
}

prod: Dict[str, str] = {
	'auth_host': 'https://auth.kheina.com',
}

assert local.keys() == dev.keys() == prod.keys()

env_vars: Dict[str, str] = locals().get(environment, local)

# add the variables from the environment to the module
locals().update(env_vars)

# delete extraneous data
del local, dev, prod, env_vars, environ


# put other variables/constants here (these will overwrite the env-specific configs above!)
epoch = 1576242000
