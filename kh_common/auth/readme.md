## Tokens

tokens consist of three parts joined by periods
- ex: `MQ.ZWQyNTUxOS5BUS5YLVM3YkEuQVEuOHcwSHdyRlRRdWFZSV9ILTZSME5pUS57ImlwIjoiMTI3LjAuMC4xIiwiZW1haWwiOiJ1c2VyQGV4YW1wbGUuY29tIn0.khpagUnfuMdzpwGlz-qGxNCqxBqPv02-1Xe4x5qdMCq33JX9p-3GnpgOTdqU-n6-nxMchZ5TjBXsPVfzJtYtCQ`


1. base64 encoded version number
	- in bytes, no further encoding is done
	- ex: `b64encode(b'1')`

2. base64 encoded token load
	- load consists of signing algorithm string, key id int, expiration timestamp int, user id int, a user-unique guid, a server-populated json blob of miscellaneous data
	- all integers base64-encoded big-endian bytes
	- miscellaneous data may include user email, ip of login location, user privileges, bot identifier, etc
	- ex: `b64encode(b'.'.join([b'ed25519', b64encode(int_to_bytes(1)), b64encode(int_to_bytes(int(datetime.now().timestamp()))), b64encode(uuid4().bytes), ujson.dumps({ 'ip': '127.0.0.1', 'email': 'user@example.com' }).encode()]))`

3. base64 encoded signature
	- includes both the load and the version number
	- ex: `private_key.sign(b64encode(b'1') + b'.' + b64encode(load))`


tokens can be used outside login context  
- verifying emails
- signin links
- any data that needs to be sent outside the server and checked for authenticity
