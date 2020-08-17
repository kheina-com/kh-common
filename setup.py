from setuptools import setup, find_packages

setup(
	name='kh_common',
	version='0.3.0',
	description='common libraries for kheina.com',
	author='kheina',
	url='https://github.com/kheina/kh-common',
	packages=find_packages(),
	install_requires=[
		'pika',
		'ujson',
	],
)