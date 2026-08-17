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
    _syncPeerCountPerOneTime:int
    _syncIntervalSec:float
    _maximumSavedDataCount:int

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
        syncPeerCountPerOneTime:int=6,
        syncIntervalSec:float=5.0,
        maximumSavedDataCount:int=100
    ) -> "Gossiper":
        """
        Create a new instance of the Gossiper class
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
        elif syncPeerCountPerOneTime <= 0:
            raise ValueError("syncPeerCountPerOneTime > 0")
        elif syncIntervalSec < 0:
            raise ValueError("syncIntervalSec >= 0")
        elif maximumSavedDataCount <= 0:
            raise ValueError("maximumSavedDataCount > 0")
        inst._gossipTTLSeconds = gossipTTLSeconds
        inst._syncPeerCountPerOneTime = syncPeerCountPerOneTime
        inst._syncIntervalSec = syncIntervalSec
        inst._maximumSavedDataCount = maximumSavedDataCount

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
        Add a new gossip message to the gossiper.
        """
        return await self._gossipBytesToFoundTimesAndAddrs.atomic(self._addGossipForAtomic, gossipB, addr)

    async def deleteGossip(self, gossipB:bytes) -> bool:
        """
        Delete a gossip message from the gossiper.
        """
        return bool(await self._gossipBytesToFoundTimesAndAddrs.delete(gossipB))

    async def getAllGossipData(self) -> list[bytes]:
        """
        Get all gossip data from the gossiper.
        """
        return list(await self._gossipBytesToFoundTimesAndAddrs.getAll())

    async def handle(self, data:bytes, addr:tuple[str, int]) -> None:
        addedCount = 0
        while len(data) >= self._gossipLength and addedCount <= self._maximumGossipCountPerMessage:
            gossipB, data = BytesSplitter.split(data, self._gossipLength, includeRest=True)
            if await self.addGossip(gossipB, addr):
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
        Synchronize gossip messages with a random selection of peers.
        This method retrieves all current gossip messages and a list of peer addresses, then sends a subset of the gossip messages to a random selection of peers. The number of peers and the number of gossip messages sent are limited by the configuration parameters.
        """
        await self._gc()

        gossips = list((await self._gossipBytesToFoundTimesAndAddrs.getAll()).items())
        if not gossips:
            return
        
        addrs = list(await self._getAddrsFunc())
        if not addrs:
            return
        
        for addr in random.sample(addrs, min(self._syncPeerCountPerOneTime, len(addrs))):
            selectedGossips = random.sample(
                gossips,
                min(self._maximumGossipCountPerMessage, len(gossips))
            )
            payload = b"".join(
                gossip[0]
                for gossip in selectedGossips
                if gossip[1][1] != addr
            )
            self._gossip(addr, payload)

    async def _syncer(self) -> None:
        while True:
            await self.sync()

            await asyncio.sleep(self._syncIntervalSec)

    async def begin(self) -> None:
        """
        Start the gossiper's synchronization task.
        If you want to see details about the gossiper, you should only call Gossiper.sync.
        """
        self._syncerTask = asyncio.create_task(self._syncer())

    async def end(self) -> None:
        """
        End the gossiper's synchronization task.
        """
        if not self._syncerTask:
            return
        self._syncerTask.done()