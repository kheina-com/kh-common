try :
	from re import _pattern_type as Pattern
	from re import compile as re_compile
except ImportError :
	from re import Pattern, compile as re_compile

from collections import defaultdict
from typing import Callable, Dict, Iterable, Iterator, List


_tagOperators: Dict[str, Callable] = defaultdict(lambda : normalizeTag, {
	'/a': str.lower,
	'/r': str.lower,
	'/l': lambda x : x[:-2],
})

_repetitionCount = 3

_repetitionRegex: Pattern = re_compile(r'(\w+?)\1{' + str(_repetitionCount) +  r',}')

_tagReplaceRegex: Pattern = re_compile(r'[-_]+')


def normalizeTag(tag: str) -> str :
	return _repetitionRegex.sub(lambda x: x.group(1) * _repetitionCount, _tagReplaceRegex.sub('_', '_'.join(tag.split())).strip('-_').lower())


def stripTags(tags: Iterable[str]) -> Iterator[str] :
	for tag in tags :
		yield tag
		tag = tag.rstrip('s')
		yield tag
		yield tag.rstrip('e')


def tagSplit(tags: List[str]) -> Iterator[str] :
	return map(lambda x : _tagOperators[x[-2:]](x), filter(None, map(str.strip, tags.split(','))))
