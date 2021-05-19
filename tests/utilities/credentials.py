from kh_common.config import credentials


def injectCredentials(**kwargs) :
	for credential, value in kwargs.items() :
		setattr(credentials, credential, value)
