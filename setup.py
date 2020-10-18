from kh_common import __version__ as kh_version
from setuptools import setup, find_packages


setup(
	name='kh_common',
	version=kh_version,
	description='common libraries for kheina.com',
	author='kheina',
	url='https://github.com/kheina-com/kh-common',
	packages=find_packages(),
	install_requires=open('requirements.txt').read().split(),
)