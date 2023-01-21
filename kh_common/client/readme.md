## Client
Defines a fuzz.ly client that can accept a bot token and self-manage authentication


## Usage
Initialize your client with or without a client token provided by the account service

```python
from kh_common.client import Client

# token received from https://account.fuzz.ly/v1/bot_create
token: str = 'aGV5IG1hbi4gaXQncyB3ZWlyZCB0aGF0IHlvdSBsb29rZWQgYXQgdGhpcywgYnV0IHRoaXMgaXNuJ3QgYSByZWFsIHRva2Vu'
fuzzly_client: Client = Client(token)
```

At this point, your client can be used to inject credentials into `kh_common.gateway.Gateway` objects

```python
from kh_common.gateway import Gateway
from kh_common.config.constants import post_host
from models import Post  # a pydantic model used to decode post responses

# fetch a post
fetch_post: Gateway = fuzzly_client.authenticated(Gateway(post_host + '/v1/post/{post_id}', Post, 'GET'))

post: Post = await fetch_post(post_id='abcd1234')  # credentials are automatically injected
```

Because `Client.authenticated` is just a decorator, you can use it on your own functions to inject credentials automatically
```python
import aiohttp
from typing import Any, Dict


@fuzzly_client.authenticated
async def fetch_post(post_id: str, auth: str = None) -> Dict[str, Any] :
	# auth is a str object containing a valid fuzz.ly authorization bearer token
	async with aiohttp.request(
		'GET',
		post_host + f'/v1/post/{post_id}',
		headers = { authorization: 'Bearer ' + auth },
		timeout = aiohttp.ClientTimeout(30),
		raise_for_status = True,
	) as response :
		return await response.json()
```
