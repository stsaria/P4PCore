import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from P4PCore.common.model.NodeIdentify import NodeIdentify
from P4PCore.common.model.HashableEd25519PublicKey import HashableEd25519PublicKey
from P4PCore.plugin.append.nodeGossiper.event.NodeGossipRecvedEvent import NodeGossipRecvedEvent
from P4PCore.plugin.append.nodeGossiper.NodeGossiper import NodeGossiper


class TestNodeGossiper:
    @pytest.fixture
    def mockRunner(self):
        runner = MagicMock()
        runner.getLogger.return_value = MagicMock()
        runner.ed25519Signer.publicKey = HashableEd25519PublicKey(b"\x01" * 32)
        runner.eventsManager = MagicMock()
        runner.pingPongNet = AsyncMock()
        return runner

    @pytest.mark.asyncio
    async def testInitialization(self, mockRunner):
        with pytest.raises(ValueError):
            NodeGossiper(mockRunner, pingTimeoutSeconds=0)

        with pytest.raises(ValueError):
            NodeGossiper(mockRunner, aliveTimeSeconds=-1.0)

        with patch("P4PCore.plugin.append.nodeGossiper.NodeGossiper.Gossiper") as mockGossiperClass:
            gossiper = NodeGossiper(mockRunner)
            assert gossiper._pingTimeoutSeconds == 1.0
            mockRunner.eventsManager.registerListener.assert_called_once_with(gossiper)

    @pytest.mark.asyncio
    async def testAddAndDeleteNode(self, mockRunner):
        with patch("P4PCore.plugin.append.nodeGossiper.NodeGossiper.Gossiper") as mockGossiperClass:
            gossiperInstance = mockGossiperClass.return_value
            gossiperInstance.addGossip.return_value = True

            gossiper = NodeGossiper(mockRunner)
            nodeIdentify = NodeIdentify(
                ip="192.168.1.1",
                port=8080,
                hashableEd25519PublicKey=HashableEd25519PublicKey(b"\x02" * 32)
            )

            result = gossiper.addNode(nodeIdentify)
            assert result is True
            gossiperInstance.addGossip.assert_called_once()

            gossiper.deleteNode(nodeIdentify)
            gossiperInstance.deleteGossip.assert_called_once()

    @pytest.mark.asyncio
    async def testOnNodeGossipRecvedAlreadyAlive(self, mockRunner):
        with patch("P4PCore.plugin.append.nodeGossiper.NodeGossiper.Gossiper") as mockGossiperClass:
            gossiperInstance = mockGossiperClass.return_value
            gossiperInstance.addGossip.return_value = True

            gossiper = NodeGossiper(mockRunner)
            nodeIdentify = NodeIdentify(
                ip="192.168.1.2",
                port=8080,
                hashableEd25519PublicKey=HashableEd25519PublicKey(b"\x03" * 32)
            )

            gossiper._alivedNodesAndFoundTimes[nodeIdentify.addr] = None

            event = MagicMock(spec=NodeGossipRecvedEvent)
            event.recvedNode = nodeIdentify
            event.addr = nodeIdentify.addr

            await gossiper.onNodeGossipRecved(event)

            assert nodeIdentify in gossiper._addNodesQueue
            gossiperInstance.addGossip.assert_called()

    @pytest.mark.asyncio
    async def testCheckAndAddNodeLoopProcessing(self, mockRunner):
        with patch("P4PCore.plugin.append.nodeGossiper.NodeGossiper.Gossiper") as mockGossiperClass:
            gossiperInstance = mockGossiperClass.return_value
            gossiperInstance.addGossip.return_value = True

            mockRunner.pingPongNet.ping.return_value = True

            gossiper = NodeGossiper(mockRunner)
            nodeIdentify = NodeIdentify(
                ip="192.168.1.3",
                port=8080,
                hashableEd25519PublicKey=HashableEd25519PublicKey(b"\x04" * 32)
            )

            gossiper._addNodesQueue.add(nodeIdentify)

            task = asyncio.create_task(gossiper._checkAndAddNodeLoop())
            
            while nodeIdentify in gossiper._addNodesQueue and not task.done():
                await asyncio.sleep(0.01)

            gossiper._endEvent.set()
            gossiper._dataReadyEvent.set()
            await task

            mockRunner.pingPongNet.ping.assert_awaited_once_with(nodeIdentify.addr, gossiper._pingTimeoutSeconds)
            assert nodeIdentify.addr in gossiper._alivedNodesAndFoundTimes

    @pytest.mark.asyncio
    async def testLifecycleOnBeginAndOnEnd(self, mockRunner):
        with patch("P4PCore.plugin.append.nodeGossiper.NodeGossiper.Gossiper") as mockGossiperClass:
            gossiperInstance = mockGossiperClass.return_value
            gossiperInstance.begin = AsyncMock()
            gossiperInstance.end = AsyncMock()

            gossiper = NodeGossiper(mockRunner)

            await gossiper.onBegin()
            gossiperInstance.begin.assert_awaited_once()
            assert gossiper._checkAndAddNodeLoopTask is not None

            await gossiper.onEnd()
            gossiperInstance.end.assert_awaited_once()
            assert gossiper._endEvent.is_set()