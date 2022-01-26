from pydantic import BaseModel, conbytes, Field
from uuid import UUID, uuid4


class RefId(conbytes(max_length=16, min_length=16)) :
	pass


class Error(BaseModel) :
	refid: RefId = Field(default_factory=lambda : uuid4().bytes)
	status: int
	error: str

	class Config:
		json_encoders = {
			bytes: lambda x : x.hex(),
		}
