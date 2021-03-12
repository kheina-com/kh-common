import ujson


class MockResponse :

	def __init__(self, load) :
		if isinstance(load, str) :
			self.text = self.content = text
		elif isinstance(load, dict) :
			self.text = ujson.dumps(load)


	def json(self) :
		return ujson.loads(self.text)
