from re import compile as re_compile
from collections import defaultdict

tagOperators = defaultdict( lambda : normalizeTag, {
	'/a': str.lower,
	'/r': str.lower,
	'/l': lambda x : x[:-2],
})

repeatreplace = re_compile(r'(\w+?)\1{3,}')

tagreplace = re_compile(r'[-_]+')


def normalizeTag(tag) :
	return repeatreplace.sub(lambda x: x.group(1) * 3, tagreplace.sub('_', '_'.join(tag.split())).strip('-_').lower())


def tagSplit(tags) :
	return map(lambda x : tagOperators[x[-2:]](x), filter(None, map(str.strip, tags.split(','))))
