from kh_common.caching import CalcDict
from scipy.stats import norm


z_score = CalcDict(lambda k : norm.ppf(1-(1-k)/2))
