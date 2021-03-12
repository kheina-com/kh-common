from kh_common.config.constants import epoch
from kh_common.caching import CalcDict
from scipy.stats import norm
from math import log10, sqrt
from typing import Union


"""
resources:
	https://github.com/reddit-archive/reddit/blob/master/r2/r2/lib/db/_sorts.pyx
	https://steamdb.info/blog/steamdb-rating
	https://www.evanmiller.org/how-not-to-sort-by-average-rating.html
	https://redditblog.com/2009/10/15/reddits-new-comment-sorting-system
	https://www.reddit.com/r/TheoryOfReddit/comments/bpmd3x/how_does_hot_vs_best_vscontroversial_vs_rising/envijlj
"""


z_score = CalcDict(lambda k : norm.ppf(1-(1-k)/2))


def _sign(x: Union[int, float]) -> int :
	return (x > 0) - (x < 0)


def hot(up: int, down: int, time: float) -> float :
	s: int = up - down
	return _sign(s) * log10(max(abs(s), 1)) + (time - epoch) / 45000


def controversial(up: int, down: int) -> float :
	return (up + down)**(min(up, down)/max(up, down)) if up or down else 0


def confidence(up: int, total: int, z:float=z_score[0.8]) -> float :
	if not total :
		return 0
	phat = up / total
	return (
		(phat + z * z / (2 * total)
		- z * sqrt((phat * (1 - phat)
		+ z * z / (4 * total)) / total)) / (1 + z * z / total)
	)


def best(up: int, total: int) -> float :
	if not total :
		return 0
	s: float = up / total
	return s - (s - 0.5) * 2**(-log10(total + 1))
