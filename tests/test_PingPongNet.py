import pytest

from P4PCore.core.PingPongNet import PingPongNet
from P4PCore.manager.Events import Events
from P4PCore.core.Net import Net


class TestPingPongNet:
    @pytest.mark.asyncio
    async def testPing(self):
        events = Events()
        net = Net(events)
        await PingPongNet.create(net, events)
        await net.begin()

        events2 = Events()
        net2 = Net(events2)
        pingPongNet2 = await PingPongNet.create(net2, events2)
        await net2.begin()

        assert not await pingPongNet2.ping(net._protocolV4.transport.get_extra_info("sockname"), timeoutSecs=0.1) is None
    @pytest.mark.asyncio
    async def testPingTimeout(self):
        net = Net(Events())
        await net.begin()

        events2 = Events()
        net2 = Net(events2)
        pingPongNet2 = await PingPongNet.create(net2, events2)
        await net2.begin()

        assert await pingPongNet2.ping(net._protocolV4.transport.get_extra_info("sockname"), timeoutSecs=0.1) is None