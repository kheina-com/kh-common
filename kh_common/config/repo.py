from kh_common.utilities import stringSlice
from typing import Any, Dict, Union
from subprocess import PIPE, Popen


name: Union[str, None] = None

output: Union[bytes, None] = b''.join(Popen(['git', 'config', '--get', 'remote.origin.url'], stdout=PIPE, stderr=PIPE).communicate())
if output and not output.startswith(b'fatal'):
	name = stringSlice(output.decode(), '/', '.git')

else :
	output = b''.join(Popen(['git', 'rev-parse', '--show-toplevel'], stdout=PIPE, stderr=PIPE).communicate())
	if output and not output.startswith(b'fatal'):
		name = stringSlice(output.decode(), '/').strip()


short_hash: Union[str, None] = None

output = b''.join(Popen(['git', 'rev-parse', '--short', 'HEAD'], stdout=PIPE, stderr=PIPE).communicate())
if output and not output.startswith(b'fatal'):
	short_hash = output.decode().strip()


full_hash: Union[str, None] = None

output = b''.join(Popen(['git', 'rev-parse', 'HEAD'], stdout=PIPE, stderr=PIPE).communicate())
if output and not output.startswith(b'fatal'):
	full_hash = output.decode().strip()


del output, stringSlice, PIPE, Popen
