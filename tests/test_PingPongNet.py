import pytest

from P4PCore.P4PRunner import P4PRunner
from P4PCore.core.PingPongNet import PingPongNet
from P4PCore.manager.Events import Events
from P4PCore.core.Net import Net

class TestPingPongNet:
    @pytest.mark.asyncio
    async def testPing(self):
        runner = await P4PRunner.create()
        await runner.begin()

        runner2 = await P4PRunner.create()
        await runner2.begin()

        assert await runner2.pingPongNet.ping(runner.net._protocolV4.transport.get_extra_info("sockname"), timeoutSecs=0.1)
    @pytest.mark.asyncio
    async def testPingTimeout(self):
        net = Net(Events())
        await net.begin()

        runner2 = await P4PRunner.create()
        await runner2.begin()

        assert await runner2.pingPongNet.ping(net._protocolV4.transport.get_extra_info("sockname"), timeoutSecs=0.1) is None