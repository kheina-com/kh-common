from typing import Any, Callable, Dict, Iterable, List, Tuple, Union
from kh_common.models import KhUser
from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from ujson import dumps
from enum import Enum
from uuid import UUID


_conversions: Dict[type, Callable] = {
	datetime: str,
	Decimal: float,
	tuple: lambda x : list(map(_convert_item, filter(None, x))),
	filter: lambda x : list(map(_convert_item, filter(None, x))),
	set: lambda x : list(map(_convert_item, filter(None, x))),
	list: lambda x : list(map(_convert_item, filter(None, x))),
	dict: lambda x : dict(zip(map(str, x.keys()), map(_convert_item, x.values()))),
	zip: lambda x : dict(zip(map(str, x.keys()), map(_convert_item, x.values()))),
	Enum: lambda x : x.name,
	UUID: lambda x : x.hex,
	KhUser: lambda x : {
		'user_id': x.user_id,
		'scope': _convert_item(x.scope),
		'token': {
			'expires': _convert_item(x.token.expires),
			'guid': _convert_item(x.token.guid),
			'data': x.token.data,
		} if x.token else None,
	},
	BaseModel: lambda x : _convert_item(x.dict()),
}


def _convert_item(item: Any) -> Any :
	if isinstance(item, str) :
		return item
	for cls in type(item).__mro__ :
		if cls in _conversions :
			return _conversions[cls](item)
	return item


def json_stream(stream: Iterable) :
	return dumps(_convert_item(stream))
