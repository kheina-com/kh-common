from asyncio import AbstractEventLoop, ensure_future, sleep
from typing import Callable, Dict, Type
from kh_common.logging import LogHandler; LogHandler.logging_available = False
from kh_common.gateway import Gateway
import pytest
from aiohttp.web import Application, RouteDef, Response, Request
from aiohttp.test_utils import TestServer
import json
from pydantic import BaseModel
from aiohttp import ClientResponseError, ClientResponse


async def create_test_server(custom_handler: Callable = None, method: str = 'GET', path: str = '/') -> TestServer :
	app: Application = Application()

	async def handler(request: Request) :
		return Response(body=json.dumps({ 'success': True }).encode(), status=200, content_type='application/json')

	app.add_routes([RouteDef(method, path, custom_handler or handler, {})])
	server = TestServer(app)
	await server.start_server()
	return server


class ResponseModel(BaseModel) :
	success: bool


# @pytest.mark.asyncio
class TestGateway :

	auth: str = 'authorization'
	attempts: int = 0

	async def test_Gateway_BasicGet_GatewayReturnsModel(self) :
		async with await create_test_server() as server :
			# arrange
			url = server.make_url('/')
			gateway: Gateway = Gateway(str(url), ResponseModel)

			# act
			result: ResponseModel = await gateway()

			# assert
			assert result.success == True


	async def test_Gateway_GetNoModel_GatewayReturnsNone(self) :
		async with await create_test_server() as server :
			# arrange
			url = server.make_url('/')
			gateway: Gateway = Gateway(str(url))

			# act
			result = await gateway()

			# assert
			assert result == None


	@pytest.mark.parametrize(
		"status",
		[500, 404, 403, 502, 429],
	)
	async def test_Gateway_ServerRaisesError_GatewayYieldsError(self, status: int) :
		async def handler(request: Request) :
			return Response(body=json.dumps({ 'success': False }).encode(), status=status, content_type='application/json')

		async with await create_test_server(handler) as server :
			# arrange
			url = server.make_url('/')
			gateway: Gateway = Gateway(str(url), status_to_retry=[])

			# act & assert
			with pytest.raises(ClientResponseError) :
				await gateway()


	async def test_Gateway_ServerRaisesError_GatewayRetriesEndpoint(self) :
		self.attempts = 0

		async def handler(request: Request) :
			# 429 is a known retry error code
			self.attempts += 1
			return Response(body=json.dumps({ 'success': False }).encode(), status=429, content_type='application/json')

		async with await create_test_server(handler) as server :
			# arrange
			url = server.make_url('/')
			# manually set backoff to always be 0
			gateway: Gateway = Gateway(str(url), backoff=lambda x : 0, attempts=3)

			# act & assert
			with pytest.raises(ClientResponseError) :
				await gateway()

			# assert
			assert self.attempts == 3


	async def test_Gateway_ServerRaisesError_GatewayDoesNotRetryEndpoint(self) :
		self.attempts = 0

		async def handler(request: Request) :
			# 404 is a known error code to not attempt to retry
			self.attempts += 1
			return Response(body=json.dumps({ 'success': False }).encode(), status=404, content_type='application/json')

		async with await create_test_server(handler) as server :
			# arrange
			url = server.make_url('/')
			gateway: Gateway = Gateway(str(url), attempts=3)

			# act & assert
			with pytest.raises(ClientResponseError) :
				await gateway()

			# assert
			assert self.attempts == 1


	@pytest.mark.parametrize(
		"method",
		['GET', 'DELETE', 'OPTIONS'],
	)
	async def test_Gateway_GatewayUsesMethodWithoutBody_ParamsAreUrlEncoded(self, method: str) :
		body: Dict[str, str] = { 'hello': 'world' }

		async def handler(request: Request) :
			assert body == dict(request.query)
			return Response(body=json.dumps({ 'success': True }).encode(), status=200, content_type='application/json')

		async with await create_test_server(handler, method) as server :
			# arrange
			url = server.make_url('/')
			gateway: Gateway = Gateway(str(url), model=ResponseModel, method=method)

			# act & assert
			result = await gateway(body=body)

			# assert
			assert result.success == True


	@pytest.mark.parametrize(
		"method",
		['POST', 'PUT', 'PATCH'],
	)
	async def test_Gateway_GatewayUsesMethodWithBody_ParamsAreJsonEncoded(self, method: str) :
		body: Dict[str, str] = { 'hello': 'world' }

		async def handler(request: Request) :
			assert body == await request.json()
			return Response(body=json.dumps({ 'success': True }).encode(), status=200, content_type='application/json')

		async with await create_test_server(handler, method) as server :
			# arrange
			url = server.make_url('/')
			gateway: Gateway = Gateway(str(url), model=ResponseModel, method=method)

			# act & assert
			result = await gateway(body=body)

			# assert
			assert result.success == True


	async def test_Gateway_GatewayUsesBodyAndParams_BodyAndParamsAreEncoded(self) :
		method: str = 'POST'
		body: Dict[str, str] = { 'hello': 'world' }
		params: Dict[str, str] = { 'url': 'params' }

		async def handler(request: Request) :
			assert body == await request.json()
			assert params == dict(request.query)
			return Response(body=json.dumps({ 'success': True }).encode(), status=200, content_type='application/json')

		async with await create_test_server(handler, method) as server :
			# arrange
			url = server.make_url('/')
			gateway: Gateway = Gateway(str(url), model=ResponseModel, method=method)

			# act & assert
			result = await gateway(body=body, params=params)

			# assert
			assert result.success == True


	async def test_Gateway_GatewayUsesOnlyParams_ParamsAreEncoded(self) :
		method: str = 'POST'
		params: Dict[str, str] = { 'url': 'params' }

		async def handler(request: Request) :
			assert params == dict(request.query)
			return Response(body=json.dumps({ 'success': True }).encode(), status=200, content_type='application/json')

		async with await create_test_server(handler, method) as server :
			# arrange
			url = server.make_url('/')
			gateway: Gateway = Gateway(str(url), model=ResponseModel, method=method)

			# act & assert
			result = await gateway(params=params)

			# assert
			assert result.success == True


	async def test_Gateway_GatewayUsesUrlFormat_UrlIsFormattedAndReached(self) :
		path: str = 'biscuit'

		async def handler(request: Request) :
			return Response(body=json.dumps({ 'success': True }).encode(), status=200, content_type='application/json')

		async with await create_test_server(handler, path='/' + path) as server :
			# arrange
			url = server.make_url('/')
			gateway: Gateway = Gateway(str(url) + '{path}', model=ResponseModel)

			# act & assert
			result = await gateway(path=path)

			# assert
			assert result.success == True


	async def test_Gateway_GatewayHasNoModel_EndpointIsCalled(self) :
		self.attempts = 0

		async def handler(request: Request) :
			self.attempts += 1
			return Response(body=json.dumps({ 'success': True }).encode(), status=200, content_type='application/json')

		async with await create_test_server(handler) as server :
			# arrange
			url = server.make_url('/')
			gateway: Gateway = Gateway(str(url))

			# act & assert
			result = await gateway()

			# assert
			assert result == None
			assert self.attempts == 1


	async def test_Gateway_GatewayUsesAuth_AuthIncludedWithBearer(self) :
		async def handler(request: Request) :
			assert request.headers['authorization'] == f'Bearer {self.auth}'
			return Response(body=json.dumps({ 'success': True }).encode(), status=200, content_type='application/json')

		async with await create_test_server(handler) as server :
			# arrange
			url = server.make_url('/')
			gateway: Gateway = Gateway(str(url), ResponseModel)

			# act & assert
			result = await gateway(auth=self.auth)

			# assert
			assert result.success == True


	async def test_Gateway_GatewayUsesHeaders_HeadersIncludedWithRequest(self) :
		headers: Dict[str, str] = {
			'a': 'b',
			'c': 'd',
		}

		async def handler(request: Request) :
			assert headers == { key: request.headers.get(key) for key in headers }
			return Response(body=json.dumps({ 'success': True }).encode(), status=200, content_type='application/json')

		async with await create_test_server(handler) as server :
			# arrange
			url = server.make_url('/')
			gateway: Gateway = Gateway(str(url), ResponseModel)

			# act & assert
			result = await gateway(headers=headers)

			# assert
			assert result.success == True


	async def test_Gateway_GatewayUsesCustomDecoder_DecoderCalledByGateway(self) :
		self.attempts = 0

		async def decoder(response: ClientResponse) :
			self.attempts += 1
			return json.loads(await response.read())

		async with await create_test_server() as server :
			# arrange
			url = server.make_url('/')
			gateway: Gateway = Gateway(str(url), ResponseModel, decoder=decoder)

			# act & assert
			result = await gateway()

			# assert
			assert result.success == True
			assert self.attempts == 1
