from typing import Any, Dict, List, Tuple, Union
from uuid import uuid4


class BaseError(Exception) :
	def __init__(self, message: str, *args:Tuple[Any], refid:Union[str, type(None)]=None, logdata:Dict[str, Any]={ }, **kwargs: Dict[str, Any]) -> type(None) :
		Exception.__init__(self, message)
		self.refid: str = refid or uuid4().hex
		self.logdata: Dict[str, Any] = {
			**logdata,
			**kwargs,
		}
