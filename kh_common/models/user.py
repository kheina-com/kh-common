from kh_common.models.privacy import UserPrivacy
from kh_common.models.verified import Verified
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class User(BaseModel) :
	name: str
	handle: str
	privacy: UserPrivacy
	icon: Optional[str]
	banner: Optional[str]
	website: Optional[str]
	created: datetime
	description: Optional[str]
	verified: Optional[Verified]
	following: Optional[bool]

	def portable(self) :
		return UserPortable(
			handle = self.handle,
			privacy = self.privacy,
			icon = self.icon,
			verified = self.verified,
			following = self.following,
		)

class UserPortable(BaseModel) :
	name: str
	handle: str
	privacy: UserPrivacy
	icon: Optional[str]
	verified: Optional[Verified]
	following: Optional[bool]
