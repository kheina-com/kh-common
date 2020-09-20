from uuid import uuid4


class BaseError(Exception) :
	def __init__(self, message, *args, uuid=None, logdata={ }, **kwargs) :
		Exception.__init__(self, message)
		self.uuid = uuid or uuid4().hex
		self.logdata = {
			**logdata,
			**kwargs,
		}
