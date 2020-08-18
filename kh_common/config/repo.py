from subprocess import check_output
from kh_common import stringSlice


name = None

output = check_output(['git', 'config', '--get', 'remote.origin.url'])
if output and not output.startswith(b'fatal'):
	name = stringSlice(output.decode(), '/', '.git')

else :
	output = check_output(['git', 'rev-parse', '--show-toplevel'])
	if output and not output.startswith(b'fatal'):
		name = stringSlice(output.decode(), '/').strip()


short_hash = None

output = check_output(['git', 'rev-parse', '--short', 'HEAD'])
if output and not output.startswith(b'fatal'):
	short_hash = output.decode().strip()


full_hash = None

output = check_output(['git', 'rev-parse', 'HEAD'])
if output and not output.startswith(b'fatal'):
	full_hash = output.decode().strip()


del output, stringSlice, check_output
