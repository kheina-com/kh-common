from base64 import urlsafe_b64encode, urlsafe_b64decode


def b64encode(bytestring) :
	return urlsafe_b64encode(bytestring).strip(b'=')


def b64decode(bytestring) :
	return urlsafe_b64decode(bytestring + (4 - len(bytestring) % 4) * (b'=' if isinstance(bytestring, bytes) else '='))