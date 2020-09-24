from re import compile as re_compile, _pattern_type as Pattern
from typing import Callable, Dict, Iterator, List
from collections import defaultdict


tagOperators: Dict[str, Callable] = defaultdict(lambda : normalizeTag, {
	'/a': str.lower,
	'/r': str.lower,
	'/l': lambda x : x[:-2],
})

repeatreplace: Pattern = re_compile(r'(\w+?)\1{3,}')

tagreplace: Pattern = re_compile(r'[-_]+')


def normalizeTag(tag: str) -> str :
	return repeatreplace.sub(lambda x: x.group(1) * 3, tagreplace.sub('_', '_'.join(tag.split())).strip('-_').lower())


def tagSplit(tags: List[str]) -> Iterator[str] :
	return map(lambda x : tagOperators[x[-2:]](x), filter(None, map(str.strip, tags.split(','))))
