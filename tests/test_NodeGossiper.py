import os
import asyncio
import pytest

from P4PCore.P4PRunner import P4PRunner
from P4PCore.common.model.NodeIdentify import NodeIdentify
from P4PCore.common.model.HashableEd25519PublicKey import HashableEd25519PublicKey

from P4PCore.plugin.append.nodeGossiper.NodeGossiper import *
from P4PCore.plugin.append.nodeGossiper.event.NodeGossipRecvedEvent import NodeGossipRecvedEvent
from P4PCore.plugin.append.nodeGossiper.util.NodeIdentifyConverter import nodeIdentifyToBytes


def _makeNode(port: int = 12345, ip: str = "127.0.0.1") -> NodeIdentify:
    return NodeIdentify(
        ip=ip,
        port=port,
        hashableEd25519PublicKey=HashableEd25519PublicKey(os.urandom(32)),
    )

class TestNodeGossiper:
    @pytest.mark.asyncio
    async def testCreateStartsEmptyWhenStorageIsEmpty(self):
        runner = P4PRunner()
        nodeGossiper = NodeGossiper(runner)

        assert nodeGossiper.nodeIdentifies == set()
        assert nodeGossiper._gossiper.gossips == []

    @pytest.mark.asyncio
    async def testGetAddrsIncludesBootstrapNodes(self):
        bootstrapNode = ("127.0.0.1", 12345)
        runner = P4PRunner()
        nodeGossiper = NodeGossiper(runner, bootstrapNodes={bootstrapNode})

        assert await nodeGossiper.getAddrs() == {bootstrapNode}

    @pytest.mark.asyncio
    async def testBootstrapNodeDiscoversPeersWithoutPreloadedGossip(self):
        seedRunner = P4PRunner()
        seedGossiper = NodeGossiper(seedRunner, syncIntervalSeconds=0.05)
        joiningRunner = P4PRunner()

        await seedRunner.begin()
        await seedGossiper.begin()
        seedAddr = seedRunner.net._protocolV4.transport.get_extra_info("sockname")
        joiningGossiper = NodeGossiper(
            joiningRunner,
            syncIntervalSeconds=0.05,
            pingTimeoutSeconds=0.5,
            bootstrapNodes={seedAddr},
        )

        try:
            await joiningRunner.begin()
            await joiningGossiper.begin()
            deadline = asyncio.get_running_loop().time() + 3
            while asyncio.get_running_loop().time() < deadline:
                if (
                    any(node.addr == seedAddr for node in joiningGossiper.nodeIdentifies)
                    and any(
                        node.addr
                        == joiningRunner.net._protocolV4.transport.get_extra_info("sockname")
                        for node in seedGossiper.nodeIdentifies
                    )
                ):
                    break
                await asyncio.sleep(0.05)

            assert any(node.addr == seedAddr for node in joiningGossiper.nodeIdentifies)
            assert any(
                node.addr
                == joiningRunner.net._protocolV4.transport.get_extra_info("sockname")
                for node in seedGossiper.nodeIdentifies
            )
        finally:
            await joiningGossiper.end()
            await joiningRunner.end()
            await seedGossiper.end()
            await seedRunner.end()

    @pytest.mark.asyncio
    async def testAddNode(self):
        runner = P4PRunner()
        nodeGossiper = NodeGossiper(runner)
        await runner.begin()

        node = _makeNode()
        assert nodeGossiper.addNode(node)
        assert node in nodeGossiper.nodeIdentifies
        assert nodeIdentifyToBytes(node) in nodeGossiper._gossiper.gossips

    @pytest.mark.asyncio
    async def testAddNodeDuplicateReturnsFalse(self):
        runner = P4PRunner()
        nodeGossiper = NodeGossiper(runner)
        await runner.begin()

        node = _makeNode()
        assert nodeGossiper.addNode(node)
        assert not nodeGossiper.addNode(node)
        assert len(nodeGossiper.nodeIdentifies) == 1

    @pytest.mark.asyncio
    async def testAddNodeRollsBackStorageWhenGossiperIsFull(self):
        runner = P4PRunner()
        nodeGossiper = NodeGossiper(runner, maximumNodesCount=1)
        await runner.begin()

        firstNode = _makeNode()
        secondNode = _makeNode(port=11235)

        assert nodeGossiper.addNode(firstNode)
        assert not nodeGossiper.addNode(secondNode)

        nodeIdentifies = nodeGossiper.nodeIdentifies
        assert firstNode in nodeIdentifies
        assert secondNode not in nodeIdentifies

    @pytest.mark.asyncio
    async def testDeleteNode(self):
        runner = P4PRunner()
        nodeGossiper = NodeGossiper(runner)
        await runner.begin()

        node = _makeNode()
        nodeGossiper.addNode(node)

        nodeGossiper.deleteNode(node)
        assert node not in nodeGossiper.nodeIdentifies
        assert nodeIdentifyToBytes(node) not in nodeGossiper._gossiper.gossips

    @pytest.mark.asyncio
    async def testOnNodeGossipRecvedAddsValidNodeToStorage(self):
        runner = P4PRunner()

        runner2 = P4PRunner()
        nodeGossiper2 = NodeGossiper(runner2)
        await runner.begin()
        await runner2.begin()
        await nodeGossiper2.begin()

        addr = runner._net._protocolV4.transport.get_extra_info("sockname")
        node = NodeIdentify(ip=addr[0], port=addr[1], hashableEd25519PublicKey=runner.ed25519Signer.publicKey)
        event = NodeGossipRecvedEvent(nodeIdentifyToBytes(node), node.addr)
        await nodeGossiper2.onNodeGossipRecved(event)

        await asyncio.sleep(0.1)

        assert node in nodeGossiper2.nodeIdentifies

    @pytest.mark.asyncio
    async def testOnNodeGossipRecvedIgnoresInvalidData(self):
        runner = P4PRunner()
        nodeGossiper = NodeGossiper(runner)
        await runner.begin()

        garbage = os.urandom(GOSSIP_SIZE)
        event = NodeGossipRecvedEvent(garbage, ("127.0.0.1", 9999))
        await nodeGossiper.onNodeGossipRecved(event)

        assert nodeGossiper.nodeIdentifies == set()

        await runner.end()

    @pytest.mark.asyncio
    async def testEndToEndGossipPropagatesNodeBetweenPeers(self):
        runner = P4PRunner()
        nodeGossiper = NodeGossiper(runner)
        await runner.begin()
        await nodeGossiper.begin()
        
        runner2 = P4PRunner()
        nodeGossiper2 = NodeGossiper(runner2)
        await runner2.begin()

        await asyncio.sleep(0)

        addr = runner2._net._protocolV4.transport.get_extra_info("sockname")
        node = NodeIdentify(ip = addr[0], port = addr[1], hashableEd25519PublicKey=runner2.ed25519Signer.publicKey)
        nodeGossiper2.addNode(node)

        nodeGossiper2._gossiper._gossip(
            runner._net._protocolV4.transport.get_extra_info("sockname"),
            nodeIdentifyToBytes(node)
        )

        await asyncio.sleep(0.1)

        assert node in nodeGossiper.nodeIdentifies