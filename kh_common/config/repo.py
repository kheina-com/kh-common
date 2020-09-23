from subprocess import check_output
from kh_common import stringSlice
from typing import Any, Dict, Union


name: Union[str, type(None)] = None

output: Union[bytes, type(None)] = check_output(['git', 'config', '--get', 'remote.origin.url'])
if output and not output.startswith(b'fatal'):
	name = stringSlice(output.decode(), '/', '.git')

else :
	output = check_output(['git', 'rev-parse', '--show-toplevel'])
	if output and not output.startswith(b'fatal'):
		name = stringSlice(output.decode(), '/').strip()


short_hash: Union[str, type(None)] = None

output = check_output(['git', 'rev-parse', '--short', 'HEAD'])
if output and not output.startswith(b'fatal'):
	short_hash = output.decode().strip()


full_hash: Union[str, type(None)] = None

output = check_output(['git', 'rev-parse', 'HEAD'])
if output and not output.startswith(b'fatal'):
	full_hash = output.decode().strip()


del output, stringSlice, check_output
