from typing import Any, Dict, List, Tuple, Union
from uuid import UUID, uuid4


class BaseError(Exception) :
	def __init__(self, message: str, *args:Tuple[Any], refid:Union[UUID, str, None]=None, logdata:Dict[str, Any]={ }, **kwargs: Dict[str, Any]) -> None :
		Exception.__init__(self, message)

		self.refid: str = refid or logdata.get('refid') or uuid4()

		if isinstance(self.refid, (str, bytes)) :

			if len(self.refid) == 32 :
				self.refid = UUID(hex=self.refid)

			elif len(self.refid) == 16 :
				self.refid = UUID(bytes=self.refid)

			else :
				raise ValueError('badly formed refid.')

		if 'refid' in logdata :
			del logdata['refid']

		self.logdata: Dict[str, Any] = {
			**logdata,
			**kwargs,
		}
