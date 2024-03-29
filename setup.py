try :
	from re import _pattern_type as Pattern
	from re import compile as re_compile
except ImportError :
	from re import Pattern, compile as re_compile

from os import listdir

from setuptools import find_packages, setup

from kh_common import __version__ as kh_version


req_regex: Pattern = re_compile(r'^requirements-(\w+).txt$')


setup(
	name='kh_common',
	version=kh_version,
	description='common libraries for kheina.com',
	long_description=open('readme.md').read(),
	long_description_content_type='text/markdown',
	author='kheina',
	url='https://github.com/kheina-com/kh-common',
	packages=find_packages(exclude=['tests']),
	install_requires=list(filter(None, map(str.strip, open('requirements.txt').read().split()))),
	python_requires='>=3.9.*',
	license='Mozilla Public License 2.0',
	extras_require=dict(map(lambda x : (x[1], open(x[0]).read().split()), filter(None, map(req_regex.match, listdir())))),
)