import os

from P4PCore.P4PRunner import P4PRunner
from P4PCore.common.manager.Events import EventListener
from P4PCore.common.model.HashableEd25519PublicKey import HashableEd25519PublicKey
from P4PCore.common.model.NodeIdentify import NodeIdentify
from P4PCore.plugin.append.nodeGossiper.NodeGossiper import NodeGossiper
from P4PCore.plugin.append.nodeGossiper.event.NodeAddedToGossiperEvent import NodeAddedToGossiperEvent

class TestNodeAddedToGossiperEvent:
    def testNodeAddedToGossiperEventTriggered(self):
        runner = P4PRunner()
        nodeGossiper = NodeGossiper(runner)

        receiveds: list[NodeAddedToGossiperEvent] = []

        class NodeAddedListner:
            @EventListener
            def onNodeAdded(self, event:NodeAddedToGossiperEvent):
                receiveds.append(event)

        runner.eventsManager.registerListener(NodeAddedListner())

        node = NodeIdentify(
            ip="127.0.0.1",
            port=12345,
            hashableEd25519PublicKey=HashableEd25519PublicKey(os.urandom(32))
        )
        nodeGossiper._pingCallbackForAddNode(node)

        assert len(receiveds) == 1
        assert receiveds[0].addedNodeIdentify == node
