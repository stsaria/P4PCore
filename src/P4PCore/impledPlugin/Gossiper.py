from __future__ import annotations
import asyncio
import logging
import random
from asyncio import Task
from typing import Callable, Type, Awaitable
from uuid import UUID

from P4PCore.P4PRunner import P4PRunner
from P4PCore.abstract.NetHandler import NetHandler
from P4PCore.event.GossipDeletedByGcEvent import GossipDeletedByGcEvent
from P4PCore.event.GossipRecvedEvent import GossipRecvedEvent
from P4PCore.protocol.Protocol import ENDIAN, PacketElementSize, PacketFlag
from P4PCore.manager.SimpleImpls import SimpleCannotOverwriteKVManager
from P4PCore.util.BytesCoverter import *
from P4PCore.util import BytesSplitter
from P4PCore.abstract.HasLoop import HasLoop


class Gossiper(NetHandler, HasLoop):
    """Coordinate gossip propagation and garbage collection across peers in the P4P network."""
    _runner:P4PRunner
    _uuidFlag:UUID
    _gossipLength:int
    _maximumGossipCountPerMessage:int
    _getAddrsFunc:Callable[[], Awaitable[set[tuple[str, int]]]]
    _gossipRecvedEventClass:Type[GossipRecvedEvent]
    _gossipDeletedByGcEventClass:Type[GossipDeletedByGcEvent]

    _gossipBytesToFoundTimesAndAddrs:SimpleCannotOverwriteKVManager[bytes, tuple[float, tuple[str, int] | None]]
    _syncerTask:Task

    _gossipTTLSeconds:float
    _syncNodeCountPerOneTime:int
    _syncIntervalSeconds:float
    _maximumSavedDataCount:int
    _requiredGossip:bytes

    @classmethod
    async def create(
        cls,
        runner:P4PRunner,
        uuidFlag:UUID,
        gossipLength:int,
        maximumGossipCountPerMessage:int,
        getAddrsFunc:Callable[[], Awaitable[set[tuple[str, int]]]],
        gossipRecvedEventClass:Type[GossipRecvedEvent],
        gossipDeletedByGcEventClass:Type[GossipDeletedByGcEvent],
        gossipTTLSeconds:float=7.0,
        syncNodeCountPerOneTime:int=6,
        syncIntervalSeconds:float=5.0,
        maximumSavedDataCount:int=100,
        requiredGossip:bytes=b""
    ) -> "Gossiper":
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
        :param maximumSavedDataCount: The maximum number of gossip messages to save. (> 0)
        :param requiredGossip: The gossip message that is required to be shared every time (% gossipLength == 0).
        :return: An instance of the Gossiper class.
        """
        inst = cls()
        inst._runner = runner
        inst._uuidFlag = uuidFlag
        inst._gossipLength = gossipLength
        inst._maximumGossipCountPerMessage = maximumGossipCountPerMessage
        inst._getAddrsFunc = getAddrsFunc
        inst._gossipRecvedEventClass = gossipRecvedEventClass
        inst._gossipDeletedByGcEventClass = gossipDeletedByGcEventClass

        inst._gossipBytesToFoundTimesAndAddrs = SimpleCannotOverwriteKVManager()
        inst._syncerTask = None

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
        inst._gossipTTLSeconds = gossipTTLSeconds
        inst._syncNodeCountPerOneTime = syncNodeCountPerOneTime
        inst._syncIntervalSeconds = syncIntervalSeconds
        inst._maximumSavedDataCount = maximumSavedDataCount
        inst._requiredGossip = requiredGossip

        await inst._runner.userNet.registerHandler(inst._uuidFlag.bytes, inst)

        return inst

    def _addGossipForAtomic(self, d:dict[bytes, float], gossipB:bytes, addr:tuple[str, int] | None) -> bool:
        now = asyncio.get_running_loop().time()
        if not gossipB in d and len(d) < int(self._maximumSavedDataCount):
            d[gossipB] = (now, addr)
            return True
        return False

    async def addGossip(self, gossipB:bytes, addr:tuple[str, int] | None = None) -> bool:
        """
        Add a gossip payload to the local store.
        :param gossipB: The gossip payload to add.
        :param addr: The sender address associated with the gossip payload, if known.
        :return: True if the payload was added successfully; otherwise False.
        """
        return await self._gossipBytesToFoundTimesAndAddrs.atomic(self._addGossipForAtomic, gossipB, addr)

    async def deleteGossip(self, gossipB:bytes) -> bool:
        """
        Remove a gossip payload from the local store.
        :param gossipB: The gossip payload to remove.
        :return: True if the payload was removed; otherwise False.
        """
        return bool(await self._gossipBytesToFoundTimesAndAddrs.delete(gossipB))

    async def getAllGossipData(self) -> list[bytes]:
        """
        Return all currently stored gossip payloads.
        :return: A list of all gossip payloads currently tracked by the gossiper.
        """
        return list(await self._gossipBytesToFoundTimesAndAddrs.getAll())

    async def handle(self, data:bytes, addr:tuple[str, int]) -> None:
        addedCount = 0
        while addedCount <= self._maximumGossipCountPerMessage:
            gossipB, data = BytesSplitter.split(data, self._gossipLength, includeRest=True)
            addedCount += 1
            await self._runner.eventsManager.triggerEvent(
                self._gossipRecvedEventClass(gossipB, addr)
            )

    async def _gc(self) -> None:
        now = asyncio.get_running_loop().time()
        for gossipB, (addedTime, _) in (await self._gossipBytesToFoundTimesAndAddrs.getAll()).items():
            if (now - addedTime) > self._gossipTTLSeconds:
                await self._gossipBytesToFoundTimesAndAddrs.delete(gossipB)
                await self._runner.eventsManager.triggerEvent(
                    self._gossipDeletedByGcEventClass(gossipB)
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
        await self._gc()

        gossips = list((await self._gossipBytesToFoundTimesAndAddrs.getAll()).items())
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