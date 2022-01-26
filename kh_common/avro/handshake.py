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
	clientProtocol: Optional[str]
	serverHash: MD5
	meta: Optional[Dict[str, bytes]]


class HandshakeResponse(BaseModel) :
	__namespace__: str = 'org.apache.avro.ipc'
	match: HandshakeMatch
	serverProtocol: Optional[str]
	serverHash: Optional[MD5]
	meta: Optional[Dict[str, bytes]]


HandshakeRequestSchema: Schema = parse("""
{
	"type": "record",
	"name": "HandshakeRequest", "namespace":"org.apache.avro.ipc",
	"fields": [
		{ "name": "clientHash", "type": { "type": "fixed", "name": "MD5", "size": 16 } },
		{ "name": "clientProtocol", "type": ["null", "string"] },
		{ "name": "serverHash", "type": "MD5" },
		{ "name": "meta", "type": ["null", { "type": "map", "values": "bytes" }] }
	]
}
""")


HandshakeResponseSchema: Schema = parse("""
{
	"type": "record",
	"name": "HandshakeResponse", "namespace": "org.apache.avro.ipc",
	"fields": [
		{ "name": "match", "type": { "type": "enum", "name": "HandshakeMatch", "symbols": ["BOTH", "CLIENT", "NONE"] } },
		{ "name": "serverProtocol", "type": ["null", "string"] },
		{ "name": "serverHash", "type": ["null", { "type": "fixed", "name": "MD5", "size": 16 }] },
		{ "name": "meta", "type": ["null", { "type": "map", "values": "bytes" }] }
	]
}
""")


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
	meta: Dict[str, bytes] = { }  # a map with values of type bytes
	messageName: str  # an Avro string, this is used as lookup key in the response handshake's messages field
	parameters: bytes  # parameters are serialized according to the message's request declaration


class CallResponse(BaseModel) :
	meta: Dict[str, bytes] = { }  # a map with values of type bytes
	error: bool  # a one-byte error flag boolean, followed by either:
	# if the error flag is false, the message response, serialized per the message's response schema.
	# if the error flag is true, the error, serialized per the message's effective error union schema.
	messageResponse: bytes
