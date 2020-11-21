from typing import Any, Callable, Dict, Iterable, List, Tuple, Union
from datetime import datetime
from decimal import Decimal


_conversions: Dict[type, Callable] = {
	datetime: datetime.timestamp,
	Decimal: float,
	tuple: lambda x : list(filter(None, x)),
	list: lambda x : list(filter(None, x)),
}


def _convert_item(item: Any) -> Any :
	if isinstance(item, Iterable) :
		return json_stream(item)

	item_type = type(item)
	if item_type in _conversions :
		return _conversions[item_type](item)

	return item


def json_stream(stream: Iterable) :
	if isinstance(stream, (dict, zip)) :
		return dict(zip(stream.keys(), map(_convert_item, stream.values())))

	else :
		return list(map(_convert_item, stream))
