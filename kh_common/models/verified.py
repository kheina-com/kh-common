from enum import Enum, unique


@unique
class Verified(Enum) :
	artist: str = 'artist'
	mod: str = 'mod'
	admin: str = 'admin'
