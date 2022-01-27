from typing import Dict, List, Optional, Union
from pydantic import BaseModel, conbytes
from avro.schema import parse, Schema
from enum import Enum


class MD5(conbytes(min_length=16, max_length=16)) :
	pass


class HandshakeMatch(Enum) :
	both: str = 'BOTH'
	client: str = 'CLIENT'
	none: str = 'NONE'


class HandshakeRequest(BaseModel) :
	__namespace__: str = 'org.apache.avro.ipc'
	clientHash: MD5
	clientProtocol: Union[None, str]
	serverHash: MD5
	meta: Union[None, Dict[str, bytes]]


class HandshakeResponse(BaseModel) :
	__namespace__: str = 'org.apache.avro.ipc'
	match: HandshakeMatch
	serverProtocol: Union[None, str]
	serverHash: Union[None, MD5]
	meta: Union[None, Dict[str, bytes]]


class AvroMessage(BaseModel) :
	"""
	each 'dict' in this definition refers to a parsed avro schema. request is the 'fields' of a schema
	these can be obtained through the kh_common.avro.schema.convert_schema(Type[BaseModel]) function
	NOTE: these are never avro-encoded. only json-stringified.
	"""
	doc: Optional[str]
	types: List[dict] = []
	request: Optional[List[dict]]
	response: Optional[Union[str, dict]]
	errors: Optional[List[Union[str, dict]]]


class AvroProtocol(BaseModel) :
	"""
	NOTE: these are never avro-encoded. only json-stringified.
	"""
	namespace: str
	protocol: str
	messages: Dict[str, AvroMessage]


class CallRequest(BaseModel) :
	meta: Union[None, Dict[str, bytes]]  # a map with values of type bytes
	messageName: str  # an Avro string, this is used as lookup key in the response handshake's messages field
	request: bytes  # parameters are serialized according to the message's request declaration


class CallResponse(BaseModel) :
	meta: Union[None, Dict[str, bytes]]  # a map with values of type bytes
	error: bool  # a one-byte error flag boolean, followed by either
	# if the error flag is false, the message response, serialized per the message's response schema.
	# if the error flag is true, the error, serialized per the message's effective error union schema.
	response: bytes
