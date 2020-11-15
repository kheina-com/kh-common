from typing import Any, Dict, Union
from subprocess import PIPE, Popen
from kh_common import stringSlice


name: Union[str, type(None)] = None

try :
	output: Union[bytes, type(None)] = b''.join(Popen(['git', 'config', '--get', 'remote.origin.url'], stdout=PIPE, stderr=PIPE).communicate())
	if output and not output.startswith(b'fatal'):
		name = stringSlice(output.decode(), '/', '.git')

	else :
		output = b''.join(Popen(['git', 'rev-parse', '--show-toplevel'], stdout=PIPE, stderr=PIPE).communicate())
		if output and not output.startswith(b'fatal'):
			name = stringSlice(output.decode(), '/').strip()
except :
	pass


short_hash: Union[str, type(None)] = None

try :
	output = b''.join(Popen(['git', 'rev-parse', '--short', 'HEAD'], stdout=PIPE, stderr=PIPE).communicate())
	if output and not output.startswith(b'fatal'):
		short_hash = output.decode().strip()
except :
	pass


full_hash: Union[str, type(None)] = None

try :
	output = b''.join(Popen(['git', 'rev-parse', 'HEAD'], stdout=PIPE, stderr=PIPE).communicate())
	if output and not output.startswith(b'fatal'):
		full_hash = output.decode().strip()
except :
	pass


del output, stringSlice, PIPE, Popen
