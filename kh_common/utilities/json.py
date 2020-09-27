from typing import Any, Callable, Dict, Iterable, List, Tuple, Union
from datetime import datetime
from decimal import Decimal


_conversions: Dict[type, Callable] = {
	datetime: datetime.timestamp,
	tuple: list,
	Decimal: float,
}


def _convert_item(self, item: Any) -> Any :
	item_type = type(item)
	if item_type in _conversions :
		return _conversions[item_type](item)
	return item


def json_stream(stream: Iterable) :
	return map(_convert_item, stream)
