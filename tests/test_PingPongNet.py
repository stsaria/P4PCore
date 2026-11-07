import asyncio
import pytest
from cachetools import TTLCache

from P4PCore.P4PRunner import P4PRunner
from P4PCore.core.PingPongNet import PingPongNet
from P4PCore.common.manager.Events import Events
from P4PCore.common.manager.WaitingResponses import WaitingResponses
from P4PCore.core.Net import Net

MAGIC = b"P4P6"

class TestPingPongNet:
    def testWaitingResponsesKeepsProvidedMappingWhenEmpty(self):
        mapping = TTLCache(10, 1)
        waitingResponses = WaitingResponses(mapping)

        assert waitingResponses._mapping is mapping

    @pytest.mark.asyncio
    async def testPing(self):
        runner = P4PRunner()
        await runner.begin()

        runner2 = P4PRunner()
        await runner2.begin()

        assert await runner2.pingPongNet.ping(runner.net._protocolV4.transport.get_extra_info("sockname"), timeoutSeconds=0.1)

    @pytest.mark.asyncio
    async def testPingTimeout(self):
        net = Net(Events(), MAGIC)
        await net.begin()

        runner2 = P4PRunner()
        await runner2.begin()

        assert await runner2.pingPongNet.ping(net._protocolV4.transport.get_extra_info("sockname"), timeoutSeconds=0.1) is None

    @pytest.mark.asyncio
    async def testPingWithCallback(self):
        runner = P4PRunner()
        await runner.begin()

        runner2 = P4PRunner()
        await runner2.begin()

        event = asyncio.Event()
        received = []

        def callback(val):
            received.append(val)
            event.set()

        runner2.pingPongNet.pingWithCallback(
            runner.net._protocolV4.transport.get_extra_info("sockname"),
            False,
            callback,
            "hello"
        )

        await asyncio.wait_for(event.wait(), timeout=1.0)
        assert received == ["hello"]

    @pytest.mark.asyncio
    async def testPingWithoutTimeoutUsesConfiguredMaximum(self):
        runner = P4PRunner()
        await runner.begin()
        runner.pingPongNet._pingAliveTimeSeconds = 0.1

        started = asyncio.get_running_loop().time()
        result = await runner.pingPongNet.ping(("127.0.0.1", 1))
        elapsed = asyncio.get_running_loop().time() - started

        assert result is None
        assert elapsed >= 0.09

    @pytest.mark.asyncio
    async def testPingTimeoutIsCappedAtConfiguredMaximum(self):
        runner = P4PRunner()
        await runner.begin()
        runner.pingPongNet._pingAliveTimeSeconds = 0.1

        started = asyncio.get_running_loop().time()
        result = await runner.pingPongNet.ping(
            ("127.0.0.1", 1),
            timeoutSeconds=1,
        )
        elapsed = asyncio.get_running_loop().time() - started

        assert result is None
        assert elapsed < 0.5
