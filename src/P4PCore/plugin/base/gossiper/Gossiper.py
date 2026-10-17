from __future__ import annotations
import asyncio
import random
from asyncio import Task
from collections.abc import Callable, Awaitable
import time
from uuid import UUID

from P4PCore.P4PRunner import P4PRunner
from P4PCore.core.abstract.NetHandler import NetHandler
from P4PCore.plugin.base.gossiper.event.GossipRecvedEvent import GossipRecvedEvent
from P4PCore.core.protocol.Protocol import PacketElementSize, PacketFlag
from P4PCore.common.util.BytesCoverter import *
from P4PCore.common.util import BytesSplitter
from P4PCore.common.abstract.HasLoop import HasLoop
from P4PCore.common.manager.MinCountTTLCache import MinCountTTLCache


class Gossiper(NetHandler, HasLoop):
    """
    Coordinate gossip propagation and garbage collection across peers in the P4P network.
    You can't send messages securely by this class.
    """
    def __init__(
        self,
        runner:P4PRunner,
        uuidFlag:UUID,
        gossipLength:int,
        maximumGossipCountPerMessage:int,
        getAddrsFunc:Callable[[], Awaitable[set[tuple[str, int]]]],
        gossipRecvedEventClass:type[GossipRecvedEvent],
        gossipTTLSeconds:float=7.0,
        syncNodeCountPerOneTime:int=6,
        syncIntervalSeconds:float=5.0,
        maximumSavedDataCount:int=100,
        requiredGossip:bytes=b"",
        minimumSavedDataCount:int=20
    ):
        """
        Create a new instance of the Gossiper class
        :param runner: The P4PRunner instance to use for networking and event management.
        :param uuidFlag: A UUID flag to identify the gossiper in the network.
        :param gossipLength: The length of each gossip message in bytes.
        :param maximumGossipCountPerMessage: The maximum number of gossip messages to send in one message.
        :param getAddrsFunc: A callable that returns a set of node addrs.
        :param gossipRecvedEventClass: The class to use for the GossipRecvedEvent.
        :param gossipDeletedByGcEventClass: The class to use for the GossipDeletedByGcEvent.
        :param gossipTTLSeconds: The time-to-live for each gossip message in seconds (> 0).
        :param syncNodeCountPerOneTime: The number of nodes to synchronize with in one time (> 0).
        :param syncIntervalSeconds: The interval between synchronization attempts in seconds (>= 0).
        :param maximumSavedDataCount: The maximum number of gossip messages to save (> 0).
        :param requiredGossip: The gossip message that is required to be shared every time (% gossipLength == 0).
        :param minimumSavedDataCount: The minimum number of gossip messages to save. If saved data size is less than this, no messages will be deleted (>= 0).
        :return: An instance of the Gossiper class.
        """

        if gossipTTLSeconds <= 0:
            raise ValueError("gossipTTLSeconds > 0")
        elif syncNodeCountPerOneTime <= 0:
            raise ValueError("syncNodeCountPerOneTime > 0")
        elif syncIntervalSeconds < 0:
            raise ValueError("syncIntervalSec >= 0")
        elif maximumSavedDataCount <= 0:
            raise ValueError("maximumSavedDataCount > 0")
        elif len(requiredGossip) % gossipLength != 0:
            raise ValueError("len(requiredGossip) % gossipLength == 0")
        elif minimumSavedDataCount < 0:
            raise ValueError("minimumSavedDataCount >= 0")

        self._runner:P4PRunner = runner
        self._uuidFlag:UUID = uuidFlag
        self._gossipLength:int = gossipLength
        self._maximumGossipCountPerMessage:int = maximumGossipCountPerMessage
        self._getAddrsFunc:Callable[[], Awaitable[set[tuple[str, int]]]] = getAddrsFunc
        self._gossipRecvedEventClass:type[GossipRecvedEvent] = gossipRecvedEventClass

        self._gossipBytesToFoundTimesAndAddrs:MinCountTTLCache[bytes, tuple[float, tuple[str, int] | None]] = MinCountTTLCache(maximumSavedDataCount, gossipTTLSeconds, minimumSavedDataCount)

        self._syncerTask:Task | None = None
        
        self._syncNodeCountPerOneTime:int = syncNodeCountPerOneTime
        self._syncIntervalSeconds:float = syncIntervalSeconds
        self._requiredGossip:bytes = requiredGossip
        self._minimumSavedDataCount:int = minimumSavedDataCount
        self._maximumSavedDataCount:int = maximumSavedDataCount

        self._runner.userNet.registerHandler(self._uuidFlag.bytes, self)

    def addGossip(self, gossipB:bytes, addr:tuple[str, int] | None = None) -> bool:
        """
        Add a gossip payload to the local store.
        :param gossipB: The gossip payload to add.
        :param addr: The sender address associated with the gossip payload, if known.
        :return: True if the payload was added successfully; otherwise False.
        """
        now = time.monotonic()
        if (
            not gossipB in self._gossipBytesToFoundTimesAndAddrs
            and
            len(self._gossipBytesToFoundTimesAndAddrs) < int(self._maximumSavedDataCount)
        ):
            self._gossipBytesToFoundTimesAndAddrs[gossipB] = (now, addr)
            return True
        return False

    def deleteGossip(self, gossipB:bytes) -> bool:
        """
        Remove a gossip payload from the local store.
        :param gossipB: The gossip payload to remove.
        :return: True if the payload was removed; otherwise False.
        """
        return not not self._gossipBytesToFoundTimesAndAddrs.pop(gossipB, False)

    @property
    def gossips(self) -> list[bytes]:
        """
        A list of all gossip payloads currently tracked by the gossiper.
        """
        return list(self._gossipBytesToFoundTimesAndAddrs)

    async def handle(self, data:bytes, addr:tuple[str, int]) -> None:
        for _ in range(self._maximumGossipCountPerMessage):
            if len(data) < self._gossipLength:
                return
            gossip, data = BytesSplitter.split(data, self._gossipLength, includeRest=True)
            if gossip in self._gossipBytesToFoundTimesAndAddrs:
                continue
            await self._runner.eventsManager.triggerEvent(
                self._gossipRecvedEventClass(gossip, addr)
            )

    def _gossip(self, addr:tuple[str, int], payload:bytes) -> None:
        self._runner.net.sendTo(
            itob(PacketFlag.USER, PacketElementSize.PACKET_FLAG)
            +self._uuidFlag.bytes
            +payload,
            addr
        )

    async def sync(self) -> None:
        """
        Synchronize gossip messages with a random selection of nodes.
        """

        gossips = list(self._gossipBytesToFoundTimesAndAddrs.items())
        if not gossips:
            return

        addrs = list(await self._getAddrsFunc())
        if not addrs:
            return

        for addr in random.sample(addrs, min(self._syncNodeCountPerOneTime, len(addrs))):
            selectedGossips = random.sample(
                gossips,
                min(self._maximumGossipCountPerMessage, len(gossips))
            )
            payload = self._requiredGossip + b"".join(
                gossip[0]
                for gossip in selectedGossips
                if gossip[1][1] != addr
            )

            self._gossip(addr, payload)

    async def _syncer(self) -> None:
        while True:
            await self.sync()

            await asyncio.sleep(self._syncIntervalSeconds)

    async def begin(self) -> None:
        """
        Start the background gossip synchronization task.
        """
        self._syncerTask = asyncio.create_task(self._syncer())

    async def end(self) -> None:
        """
        Stop the background gossip synchronization task.
        """
        if not self._syncerTask:
            return
        self._syncerTask.done()
