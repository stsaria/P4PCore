from asyncio import Event, AbstractEventLoop, Task
import asyncio
from enum import IntEnum
import uuid
from uuid import UUID
from cachetools import TTLCache

from P4PCore.P4PRunner import Logger, P4PRunner
from P4PCore.plugin.base.gossiper.Gossiper import Gossiper
from P4PCore.core.protocol.Protocol import SecurePacketElementSize
from P4PCore.common.manager.Events import EventListener
from P4PCore.common.model.NodeIdentify import NodeIdentify
from P4PCore.common.util.BytesCoverter import *
from P4PCore.plugin.append.nodeGossiper.event.NodeGossipRecvedEvent import NodeGossipRecvedEvent
from P4PCore.plugin.append.nodeGossiper.protocol.Protocol import *
from P4PCore.plugin.append.nodeGossiper.util.NodeIdentifyConverter import *


BASE_PLUGIN_UUID_HEX = "27416bf84dbd4a448cc12adf238aa5f6"
PROTOCOL_VERSION = "1"
PLUGIN_UUID = uuid.uuid5(UUID(hex=BASE_PLUGIN_UUID_HEX), PROTOCOL_VERSION)

GOSSIP_SIZE = (
    NodeGossiperPacketElementSize.IP_ADDR_FAMILY
    +NodeGossiperPacketElementSize.IP
    +NodeGossiperPacketElementSize.PORT
    +SecurePacketElementSize.ED25519_PUBLIC_KEY
)

class NodeGossiper:
    """
    A gossiper plugin that manages the gossiping of node information
    in a P2P network.
    """
    def __init__(
        self,
        runner:P4PRunner,
        gossipTTLSeconds:int=5,
        syncNodeCountPerOneTime:int=5,
        syncIntervalSeconds:float=5,
        maximumNodesCount:int=100,
        minimumNodesCount:int=20,
        pingTimeoutSeconds:float=1.0,
        aliveTimeSeconds:float=30.0,
        aliveStorageNodesCount:int=1000
    ) -> "NodeGossiper":
        """
        Create a new NodeGossiper instance.

        :param runner: The P4PRunner instance to use for networking and
            event management.
        :param gossipTTLSeconds: The time-to-live for each node gossip
            message in seconds (> 0).
        :param syncNodeCountPerOneTime: The maximum number of nodes to
            synchronize with in one synchronization (> 0).
        :param syncIntervalSeconds: The interval between synchronization
            attempts in seconds (>= 0).
        :param maximumNodesCount: The maximum number of nodes to store (> 0).
        :param minimumNodesCount: The minimum number of nodes to store (>= 0).
        :param pingTimeoutSeconds: The timeout for pinging nodes in seconds (> 0).
        :param aliveTimeSeconds: The time a node is considered alive in seconds (> 0).
        :param aliveStorageNodesCount: The maximum number of alive nodes to store (> 0).
        :return: An initialized NodeGossiper instance.
        """
        if pingTimeoutSeconds <= 0:
            raise ValueError("pingTimeoutSeconds > 0")
        elif aliveTimeSeconds <= 0:
            raise ValueError("aliveTimeSeconds > 0")
        elif aliveStorageNodesCount <= 0:
            raise ValueError("aliveStorageNodesCount > 0")

        self._runner:P4PRunner = runner

        self._gossiper:Gossiper = Gossiper(
            runner,
            PLUGIN_UUID,
            GOSSIP_SIZE,
            MAXIMUM_GOSSIP_COUNT_PER_MESSAGE,
            self.getAddrs,
            NodeGossipRecvedEvent,
            gossipTTLSeconds=gossipTTLSeconds,
            syncNodeCountPerOneTime=syncNodeCountPerOneTime,
            syncIntervalSeconds=syncIntervalSeconds,
            maximumSavedDataCount=maximumNodesCount,
            minimumSavedDataCount=minimumNodesCount,
            requiredGossip=nodeIdentifyToBytes(
                NodeIdentify(
                    ip="",
                    port=0,
                    hashableEd25519PublicKey=runner.ed25519Signer.publicKey
                )
            )
        )
        self._logger = self._runner.getLogger("NodeGossiper")
        self._alivedNodesAndFoundTimes:TTLCache[tuple[str, int], None] = TTLCache(
            aliveStorageNodesCount,
            aliveTimeSeconds
        )
        self._pingTimeoutSeconds:int = pingTimeoutSeconds
        self._addNodesQueue:set[NodeIdentify] = set()

        self._endEvent:Event = Event()
        self._dataReadyEvent:Event = Event()

        self._checkAndAddNodeLoopTask:Task | None = None

        self._runner.eventsManager.registerListener(self)
    
    def addNode(self, nodeIdentify:NodeIdentify) -> bool:
        """
        Add a node to the gossiper and node storage.

        If adding the gossip fails after the node has been added to storage,
        the storage operation is rolled back.

        :param nodeIdentify: The NodeIdentify object of the node to add.
        :return: Details on whether the node was successfully added.
        """
        if not self._gossiper.addGossip(
            nodeIdentifyToBytes(nodeIdentify),
            nodeIdentify.addr
        ):
            return False

        return True
    
    def deleteNode(self, nodeIdentify:NodeIdentify) -> None:
        """
        Remove a node from the gossiper and node storage.

        :param nodeIdentify: The NodeIdentify object of the node to remove.
        """
        self._gossiper.deleteGossip(
            nodeIdentifyToBytes(nodeIdentify)
        )

    @property
    def nodeIdentifies(self) -> set[NodeIdentify]:
        """
        All NodeIdentify objects currently stored by the gossiper.
        """
        return {bytesToNodeIdentify(n) for n in self._gossiper.gossips}

    async def getAddrs(self) -> set[NodeIdentify]:
        """
        Return the addresses of all nodes currently stored by the gossiper.

        :return: A collection of node addresses.
        """
        return {n.addr for n in self.nodeIdentifies}

    @EventListener
    async def onNodeGossipRecved(
        self,
        event:NodeGossipRecvedEvent
    ) -> None:
        recvedNode = event.recvedNode

        if recvedNode is None:
            self._logger.warning(
                "Recved invalid node gossip. gossipContent:%s",
                str(event._gossipContent)
            )
            return
        elif not (recvedNode.ip and recvedNode.port):
            # sender's info
            recvedNode = NodeIdentify(
                ip=event.addr[0],
                port=event.addr[1],
                hashableEd25519PublicKey=recvedNode.hashableEd25519PublicKey
            )
        
        if recvedNode.addr in self._alivedNodesAndFoundTimes:
            self.addNode(recvedNode)
            self._logger.debug(
                "Adding nodeId:%s",
                nodeIdentifyToBytes(recvedNode).hex()
            )
        self._addNodesQueue.add(recvedNode)
        self._dataReadyEvent.set()
        self._logger.debug(
            "Node was added to checking queue. nodeId:%s",
            nodeIdentifyToBytes(recvedNode).hex()
        )

    async def _checkAndAddNodeLoop(self) -> None:
        while not self._endEvent.is_set():
            if not self._addNodesQueue:
                await self._dataReadyEvent.wait()
                self._dataReadyEvent.clear()
                if self._endEvent.is_set():
                    break
                continue
            nodeIdentify = self._addNodesQueue.pop()
            addr = nodeIdentify.addr
            if addr in self._alivedNodesAndFoundTimes:
                continue
            if not (await self._runner.pingPongNet.ping(addr, self._pingTimeoutSeconds)):
                continue
            self._alivedNodesAndFoundTimes[addr] = None
            self.addNode(nodeIdentify)

    async def begin(self) -> None:
        """
        Start the gossiper sync task and background node checking loop.
        """
        self._logger.info("NodeGossiper sync task starting.")
        self._checkAndAddNodeLoopTask = asyncio.create_task(self._checkAndAddNodeLoop())
        await self._gossiper.begin()
    
    async def end(self) -> None:
        """
        Stop the gossiper sync task, signal events to unblock background loops, and wait for task completion.
        """
        self._logger.info("NodeGossiper sync task stopping.")
        await self._gossiper.end()
        if not self._checkAndAddNodeLoopTask:
            return
        self._endEvent.set()
        self._dataReadyEvent.set()
        await self._checkAndAddNodeLoopTask