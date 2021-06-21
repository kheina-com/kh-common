from kh_common.models.privacy import UserPrivacy
from kh_common.models.verified import Verified
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class User(BaseModel) :
	name: str
	handle: str
	privacy: UserPrivacy
	icon: str
	banner: Optional[str]
	website: Optional[str]
	created: datetime
	description: Optional[str]
	verified: Optional[Verified]


class UserPortable(BaseModel) :
	name: str
	handle: str
	privacy: UserPrivacy
	icon: str
	verified: Optional[Verified]
