from asyncio import AbstractEventLoop, ensure_future, sleep
from typing import Callable
from kh_common.logging import LogHandler; LogHandler.logging_available = False
from kh_common.gateway import Gateway
import pytest
from aiohttp.web import Application, RouteDef, Response, Request
from aiohttp.test_utils import TestServer
import json
from pydantic import BaseModel


def create_test_server(custom_handler: Callable = None) -> TestServer :
	app: Application = Application()

	async def handler(request: Request):
		return Response(body=json.dumps({ 'success': True }).encode(), status=200, content_type='application/json')

	app.add_routes([RouteDef('GET', '/', custom_handler or handler, {})])
	server = TestServer(app)
	return server


class ResponseModel(BaseModel) :
	success: bool


# @pytest.mark.asyncio
class TestGateway :

	async def test_Gateway_BasicGet_GatewayReturnsModel(self) :
		async with create_test_server() as server :
			# arrange
			await server.start_server()
			url = server.make_url('/')
			gateway: Gateway = Gateway(str(url), ResponseModel)

			# act
			result: ResponseModel = await gateway()

			# assert
			assert result.success == True
