from subprocess import PIPE, Popen
from kh_common import __version__
import re


main_branch = 'main'


class TestGit :

	def test_version_changed_in_new_branch(self) :
		current_branch = b''.join(Popen(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], stdout=PIPE, stderr=PIPE).communicate()).decode().strip()

		if current_branch == main_branch :
			return

		lib_init_file = b''.join(Popen(['git', 'show', f'{main_branch}:kh_common/__init__.py'], stdout=PIPE, stderr=PIPE).communicate()).decode().strip()

		main_version = re.search(r'''__version__.*?\=\s*['"](.+)["']''', lib_init_file)[1]

		assert __version__ != main_version
