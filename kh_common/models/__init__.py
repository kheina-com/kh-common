from pydantic import BaseModel, conbytes
from typing import List, Union


class RefId(conbytes(max_length=16, min_length=16)) :
	pass


class Error(BaseModel) :
	refid: Union[None, RefId]
	status: int
	error: str

	class Config:
		json_encoders = {
			bytes: lambda x : x.hex(),
		}


class ValidationErrorDetail(BaseModel) :
	loc: List[str]
	msg: str
	type: str


class ValidationError(BaseModel) :
	detail: List[ValidationErrorDetail]
