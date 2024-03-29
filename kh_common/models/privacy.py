from enum import Enum, unique


@unique
class Privacy(Enum) :
	public: str = 'public'
	unlisted: str = 'unlisted'
	private: str = 'private'
	unpublished: str = 'unpublished'
	draft: str = 'draft'


@unique
class UserPrivacy(Enum) :
	public: str = 'public'
	private: str = 'private'
