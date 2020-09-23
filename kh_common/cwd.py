import os

def setCwd() -> str :
	# fetch working directory
	with open('/var/local/kheina.com-dir') as cwd :
		os.chdir(cwd.read().strip())

	return os.getcwd()
