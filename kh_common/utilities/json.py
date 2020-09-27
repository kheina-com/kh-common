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
	item_type = type(item)
	if item_type in _conversions :
		return _conversions[item_type](item)
	return item


def json_stream(stream: Iterable) :
	return map(_convert_item, stream)
