from typing import Any, Callable, Dict, Iterable, List, Tuple, Union
from datetime import datetime
from decimal import Decimal
from enum import Enum


_conversions: Dict[type, Callable] = {
	datetime: datetime.timestamp,
	Decimal: float,
	tuple: lambda x : list(filter(None, x)),
	list: lambda x : list(filter(None, x)),
	Enum: lambda x : x.name,
}


def _convert_item(item: Any) -> Any :
	if isinstance(item, str) :
		return item
	if isinstance(item, Iterable) :
		return json_stream(item)
	for cls in type(item).__mro__ :
		if cls in _conversions :
			return _conversions[cls](item)
	return item


def json_stream(stream: Iterable) :
	if isinstance(stream, (dict, zip)) :
		return dict(zip(stream.keys(), map(_convert_item, stream.values())))

	else :
		return list(map(_convert_item, stream))
