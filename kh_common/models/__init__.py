from pydantic import BaseModel, conbytes, validator


class RefId(conbytes(max_length=16, min_length=16)) :
	pass


class Error(BaseModel) :
	refid: RefId
	status: int
	error: str

	class Config:
		json_encoders = {
			bytes: lambda x : x.hex(),
		}
