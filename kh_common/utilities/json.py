from typing import Any, Callable, Dict, Iterable, List, Tuple, Union
from kh_common.models import KhUser
from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID


_conversions: Dict[type, Callable] = {
	datetime: str,
	Decimal: float,
	tuple: lambda x : list(map(json_stream, filter(None, x))),
	filter: lambda x : list(map(json_stream, filter(None, x))),
	set: lambda x : list(map(json_stream, filter(None, x))),
	list: lambda x : list(map(json_stream, filter(None, x))),
	dict: lambda x : dict(zip(map(str, x.keys()), map(json_stream, x.values()))),
	zip: lambda x : dict(zip(map(str, x.keys()), map(json_stream, x.values()))),
	Enum: lambda x : x.name,
	UUID: lambda x : x.hex,
	KhUser: lambda x : {
		'user_id': x.user_id,
		'scope': json_stream(x.scope),
		'token': {
			'expires': json_stream(x.token.expires),
			'guid': json_stream(x.token.guid),
			'data': x.token.data,
		} if x.token else None,
	},
	BaseModel: lambda x : json_stream(x.dict()),
}


def json_stream(item: Any) -> Any :
	if isinstance(item, str) :
		return item
	for cls in type(item).__mro__ :
		if cls in _conversions :
			return _conversions[cls](item)
	return item
