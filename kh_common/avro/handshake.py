from avro.schema import parse, Schema
from pydantic import BaseModel
from typing import Optional
from enum import Enum


class HandshakeMatch(Enum) :
	both: str = 'BOTH'
	client: str = 'CLIENT'
	none: str = 'NONE'


class HandshakeRequest(BaseModel) :
	clientHash: bytes
	clientProtocol: Optional[str]
	serverHash: bytes


class HandshakeResponse(BaseModel) :
	match: HandshakeMatch
	serverProtocol: Optional[str]
	serverHash: Optional[bytes]


HandshakeRequestSchema: Schema = parse("""
{
	"type": "record",
	"name": "HandshakeRequest", "namespace":"org.apache.avro.ipc",
	"fields": [
		{"name": "clientHash", "type": {"type": "fixed", "name": "MD5", "size": 16}},
		{"name": "clientProtocol", "type": ["null", "string"]},
		{"name": "serverHash", "type": "MD5"},
		{"name": "meta", "type": ["null", {"type": "map", "values": "bytes"}]}
	]
}
""")


HandshakeResponseSchema: Schema = parse("""
{
	"type": "record",
	"name": "HandshakeResponse", "namespace": "org.apache.avro.ipc",
	"fields": [
		{"name": "match", "type": {"type": "enum", "name": "HandshakeMatch", "symbols": ["BOTH", "CLIENT", "NONE"]}},
		{"name": "serverProtocol", "type": ["null", "string"]},
		{"name": "serverHash", "type": ["null", {"type": "fixed", "name": "MD5", "size": 16}]},
		{"name": "meta", "type": ["null", {"type": "map", "values": "bytes"}]}
	]
}
""")
