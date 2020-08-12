from setuptools import setup, find_packages

setup(
	name='kh_common',
	version='0.2.6',
	description='common libraries for kheina.com',
	author='kheina',
	url='https://gitlab.com/kheina.com/kh-common',
	packages=find_packages(),
	install_requires=[
		'pika',
		'ujson',
	],
)