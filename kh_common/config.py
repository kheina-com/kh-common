from os import environ


environment = environ.get('ENVIRONMENT', 'LOCAL').lower()

local = {
	'admin_host': 'http://127.0.0.1:5000',
}

dev = {
	'admin_host': 'https://auth-dev.kheina.com',
}

prod = {
	'admin_host': 'https://auth.kheina.com',
}

env_vars = local
if environment == 'prod' :
	env_vars = prod
elif environment == 'dev' :
	env_vars = dev
elif environment == 'local' :
	env_vars = local


admin_host = env_vars.get('admin_host')
