from enum import Enum, unique


@unique
class Rating(Enum) :
	general: str = 'general'
	mature: str = 'mature'
	explicit: str = 'explicit'