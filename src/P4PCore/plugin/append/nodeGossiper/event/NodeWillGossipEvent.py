from P4PCore.common.model.NodeIdentify import NodeIdentify
from P4PCore.plugin.base.gossiper.event.WillGossipEvent import WillGossipEvent
from P4PCore.plugin.append.nodeGossiper.protocol.Protocol import *
from P4PCore.plugin.append.nodeGossiper.util.NodeIdentifyConverter import *

class NodeWillGossipEvent(WillGossipEvent):
    """
    Will gossip event is fired when a node is about to gossip its information to other nodes.
    If you don't want to send the gossip, you can call the cancel() method to prevent the gossip message from being sent.
    """