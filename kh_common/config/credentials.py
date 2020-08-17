from os import environ, path, listdir
from ujson import load as json_load


environment = environ.get('ENVIRONMENT', 'LOCAL').lower()

env_vars = { }

# dynamically load local credentials
if path.isdir('credentials') :
	for filename in listdir('credentials') :
		if filename.endswith('.json') :
			config = json_load(open(f'credentials/{filename}'))
			c = config.get(environment)
			if not c :
				c = config.get('prod')
			if not c :
				continue

		# add other file type logic here

		env_vars.update(c)
		del filename, config, c

# add the variables from the environment to the module
locals().update(env_vars)

# delete extraneous data
del env_vars, environment, environ, path, listdir, json_load
