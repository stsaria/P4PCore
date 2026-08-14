import asyncio
import os
from uuid import uuid4
import pytest

from P4PCore.P4PRunner import P4PRunner
from P4PCore.impledPlugin.Gossiper import Gossiper
from P4PCore.event.GossipRecvedEvent import GossipRecvedEvent
from P4PCore.event.GossipDeletedByGcEvent import GossipDeletedByGcEvent
from P4PCore.manager.Events import EventListener

PLUGIN_UUID = uuid4()
GOSSIP_LENGTH = 10
MAX_GOSSIP_COUNT_PER_MESSAGE = 10


class TestGossipDeletedByGcEvent:
    @pytest.mark.asyncio
    async def testGossipDeletedByGcEventTriggered(self):
        runner = await P4PRunner.create()

        async def getAddrs():
            return []
        gossiper = await Gossiper.create(
            runner, PLUGIN_UUID, GOSSIP_LENGTH, MAX_GOSSIP_COUNT_PER_MESSAGE,
            getAddrs, GossipRecvedEvent, GossipDeletedByGcEvent,
            gossipTTLSeconds=0.1
        )
        await runner.begin()
        await gossiper.begin()

        deleteds: list[GossipDeletedByGcEvent] = []

        class GossipDeletedListener:
            @EventListener
            async def onDeleted(self, e: GossipDeletedByGcEvent):
                deleteds.append(e)

        await runner.eventsManager.registerListener(GossipDeletedListener())

        gossipContent = os.urandom(GOSSIP_LENGTH)
        await gossiper.addGossip(gossipContent)

        await asyncio.sleep(0.2)
        await gossiper._gc()

        assert len(deleteds) == 1
        assert deleteds[0].gossipContent == gossipContent

        await gossiper.end()
        await runner.end()