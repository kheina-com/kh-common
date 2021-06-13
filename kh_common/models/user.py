from kh_common.models.privacy import Privacy
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class User(BaseModel) :
	name: str
	handle: str
	privacy: Privacy
	icon: str
	banner: Optional[str]
	website: Optional[str]
	created: datetime
	description: Optional[str]
	verified: Optional[str]
