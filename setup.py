from kh_common import __version__ as kh_version
from setuptools import setup, find_packages


setup(
	name='kh_common',
	version=kh_version,
	description='common libraries for kheina.com',
    long_description=open('readme.md').read(),
    long_description_content_type='text/markdown',
	author='kheina',
	url='https://github.com/kheina-com/kh-common',
	packages=find_packages(exclude=['tests']),
	install_requires=open('requirements.txt').read().split(),
	extras_require={
		'scoring':  ['scipy>=1.5.2'],
	},
)