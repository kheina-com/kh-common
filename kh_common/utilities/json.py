from typing import Any, Callable, Dict, Iterable, List, Tuple, Union
from kh_common.models import KhUser
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID


_conversions: Dict[type, Callable] = {
	datetime: datetime.timestamp,
	Decimal: float,
	tuple: lambda x : list(map(_convert_item, filter(None, x))),
	set: lambda x : list(map(_convert_item, filter(None, x))),
	list: lambda x : list(map(_convert_item, filter(None, x))),
	Enum: lambda x : x.name,
	UUID: lambda x : x.hex,
	KhUser: lambda x : {
		'user_id': x.user_id,
		'scope': json_stream(x.scope),
		'token': {
			'expires': x.token.expires,
			'guid': x.token.guid.hex,
			'data': x.token.data,
		} if x.token else None,
	},
}


def _convert_item(item: Any) -> Any :
	if isinstance(item, str) :
		return item
	for cls in type(item).__mro__ :
		if cls in _conversions :
			return _conversions[cls](item)
	if isinstance(item, Iterable) :
		return json_stream(item)
	return item


def json_stream(stream: Iterable) :
	if isinstance(stream, (dict, zip)) :
		return dict(zip(stream.keys(), map(_convert_item, stream.values())))

	else :
		return list(map(_convert_item, stream))
