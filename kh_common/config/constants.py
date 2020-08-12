from os import environ


environment = environ.get('ENVIRONMENT', 'LOCAL').lower()

local = {
	'auth_host': 'http://127.0.0.1:5000',
}

dev = {
	'auth_host': 'https://auth-dev.kheina.com',
}

prod = {
	'auth_host': 'https://auth.kheina.com',
}

assert local.keys() == dev.keys() == prod.keys()

env_vars = locals().get(environment, local)

# add the variables from the environment to the module
locals().update(env_vars)

# delete extraneous data
del local, dev, prod, env_vars, environment, environ


# put other variables/constants here (these will overwrite the env-specific configs above!)
