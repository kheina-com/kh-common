from asyncio import AbstractEventLoop, ensure_future, sleep
from typing import Callable, Dict, Type
from kh_common.logging import LogHandler; LogHandler.logging_available = False
from kh_common.gateway import Gateway
import pytest
from aiohttp.web import Application, RouteDef, Response, Request
from aiohttp.test_utils import TestServer
import json
from pydantic import BaseModel
from aiohttp import ClientResponseError


async def create_test_server(custom_handler: Callable = None, method: str = 'GET') -> TestServer :
	app: Application = Application()

	async def handler(request: Request):
		return Response(body=json.dumps({ 'success': True }).encode(), status=200, content_type='application/json')

	app.add_routes([RouteDef(method, '/', custom_handler or handler, {})])
	server = TestServer(app)
	await server.start_server()
	return server


class ResponseModel(BaseModel) :
	success: bool


# @pytest.mark.asyncio
class TestGateway :

	Attempts: int = 0

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
		async def handler(request: Request):
			return Response(body=json.dumps({ 'success': False }).encode(), status=status, content_type='application/json')

		async with await create_test_server(handler) as server :
			# arrange
			url = server.make_url('/')
			gateway: Gateway = Gateway(str(url), status_to_retry=[])

			# act & assert
			with pytest.raises(ClientResponseError) :
				await gateway()


	async def test_Gateway_ServerRaisesError_GatewayRetriesEndpoint(self) :
		self.Attempts: int = 0

		async def handler(request: Request):
			# 429 is a known retry error code
			self.Attempts += 1
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
			assert self.Attempts == 3


	async def test_Gateway_ServerRaisesError_GatewayDoesNotRetryEndpoint(self) :
		self.Attempts: int = 0

		async def handler(request: Request):
			# 404 is a known error code to not attempt to retry
			self.Attempts += 1
			return Response(body=json.dumps({ 'success': False }).encode(), status=404, content_type='application/json')

		async with await create_test_server(handler) as server :
			# arrange
			url = server.make_url('/')
			# manually set backoff to always be 0
			gateway: Gateway = Gateway(str(url), attempts=3)

			# act & assert
			with pytest.raises(ClientResponseError) :
				await gateway()

			# assert
			assert self.Attempts == 1


	@pytest.mark.parametrize(
		"method",
		['GET', 'DELETE', 'OPTIONS'],
	)
	async def test_Gateway_GatewayUsesMethodWithoutBody_ParamsAreUrlEncoded(self, method: str) :
		body: Dict[str, str] = { 'hello': 'world' }

		async def handler(request: Request):
			assert body == dict(request.query)
			return Response(body=json.dumps({ 'success': True }).encode(), status=200, content_type='application/json')

		async with await create_test_server(handler, method) as server :
			# arrange
			url = server.make_url('/')
			# manually set backoff to always be 0
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

		async def handler(request: Request):
			assert body == await request.json()
			return Response(body=json.dumps({ 'success': True }).encode(), status=200, content_type='application/json')

		async with await create_test_server(handler, method) as server :
			# arrange
			url = server.make_url('/')
			# manually set backoff to always be 0
			gateway: Gateway = Gateway(str(url), model=ResponseModel, method=method)

			# act & assert
			result = await gateway(body=body)

			# assert
			assert result.success == True
