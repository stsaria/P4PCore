from uuid import uuid4
import pytest
import asyncio
import os

from P4PCore.P4PRunner import P4PRunner
from P4PCore.impledPlugin.Gossiper import Gossiper
from P4PCore.event.GossipRecvedEvent import GossipRecvedEvent
from P4PCore.event.GossipDeletedByGcEvent import GossipDeletedByGcEvent
from P4PCore.manager.Events import EventListener

PLUGIN_UUID = uuid4()
GOSSIP_LENGTH = 10
MAX_GOSSIP_COUNT_PER_MESSAGE = 10

class TestGossiper:
    @pytest.mark.asyncio
    async def testGossip(self):
        runner = await P4PRunner.create()
        gossiper = await Gossiper.create(runner, PLUGIN_UUID, GOSSIP_LENGTH, MAX_GOSSIP_COUNT_PER_MESSAGE, lambda:None, GossipRecvedEvent, GossipDeletedByGcEvent)

        l = []
        gossipContent = os.urandom(GOSSIP_LENGTH)
        class GossipRecvedHandler:
            @EventListener
            async def onGossipRecved(self, e:GossipRecvedEvent):
                if e.gossipContent != gossipContent:
                    return
                l.append(1)
        await runner.eventsManager.registerListener(GossipRecvedHandler())

        await runner.begin()
        await gossiper.begin()

        runner2 = await P4PRunner.create()
        gossiper2 = await Gossiper.create(runner2, PLUGIN_UUID, GOSSIP_LENGTH, MAX_GOSSIP_COUNT_PER_MESSAGE, lambda:None, GossipRecvedEvent, GossipDeletedByGcEvent)
        await runner2.begin()
        await gossiper2.begin()

        await asyncio.sleep(0)

        gossipContent = os.urandom(GOSSIP_LENGTH)
        
        gossiper2._gossip(
            runner.net._protocolV4.transport.get_extra_info("sockname"),
            gossipContent
        )

        await asyncio.sleep(0.1)

        assert len(l)

        await gossiper.end()
        await runner.end()
        await gossiper2.end()
        await runner2.end()

    @pytest.mark.asyncio
    async def testGossipTTLAndGC(self):
        runner = await P4PRunner.create()

        async def getAddrs():
            return []
        gossiper = await Gossiper.create(
            runner, PLUGIN_UUID, GOSSIP_LENGTH, MAX_GOSSIP_COUNT_PER_MESSAGE, getAddrs,
            GossipRecvedEvent, GossipDeletedByGcEvent,
            gossipTTLSeconds=0.2
        )
        await runner.begin()
        await gossiper.begin()

        gossipContent = os.urandom(GOSSIP_LENGTH)
        await gossiper.addGossip(gossipContent)
        assert await gossiper._gossipBytesToFoundTimesAndAddrs.len() == 1

        await asyncio.sleep(0.1)
        await gossiper._gc()
        assert await gossiper._gossipBytesToFoundTimesAndAddrs.len() == 1

        await asyncio.sleep(0.2)
        await gossiper._gc()
        assert await gossiper._gossipBytesToFoundTimesAndAddrs.len() == 0

        await gossiper.end()
        await runner.end()

    @pytest.mark.asyncio
    async def testSync(self):
        runner = await P4PRunner.create()
        l = []
        gossipContent = os.urandom(GOSSIP_LENGTH)
        class GossipRecvedHandler:
            @EventListener
            async def onGossipRecved(self, e:GossipRecvedEvent):
                if e.gossipContent != gossipContent:
                    return
                l.append(1)
        await runner.eventsManager.registerListener(GossipRecvedHandler())
        runner2 = await P4PRunner.create()

        await runner.begin()

        async def getAddrs():
            return [runner._net._protocolV4.transport.get_extra_info("sockname")]

        gossiper = await Gossiper.create(
            runner, PLUGIN_UUID, GOSSIP_LENGTH, MAX_GOSSIP_COUNT_PER_MESSAGE, getAddrs,
            GossipRecvedEvent, GossipDeletedByGcEvent,
            syncIntervalSeconds=0.1, gossipTTLSeconds=10
        )
        gossiper2 = await Gossiper.create(
            runner2, PLUGIN_UUID, GOSSIP_LENGTH, MAX_GOSSIP_COUNT_PER_MESSAGE, getAddrs,
            GossipRecvedEvent, GossipDeletedByGcEvent,
            syncIntervalSeconds=1, gossipTTLSeconds=10
        )
        
        await runner2.begin()
        await gossiper2.begin()
        
        await gossiper2.addGossip(gossipContent)

        assert await gossiper._gossipBytesToFoundTimesAndAddrs.len() == 0
        assert not len(l)

        await asyncio.sleep(0.3)

        assert len(l) == 1

        await runner.end()
        await gossiper2.end()
        await runner2.end()

    @pytest.mark.asyncio
    async def testDontSyncByGricesMaximOfQuantityRule(self):
        runner = await P4PRunner.create()
        l = []
        gossipContent = os.urandom(GOSSIP_LENGTH)
        class GossipRecvedHandler:
            @EventListener
            async def onGossipRecved(self, e:GossipRecvedEvent):
                if e.gossipContent != gossipContent:
                    return
                l.append(1)
        await runner.eventsManager.registerListener(GossipRecvedHandler())
        runner2 = await P4PRunner.create()

        await runner.begin()

        async def getAddrs():
            return [runner._net._protocolV4.transport.get_extra_info("sockname")]

        gossiper = await Gossiper.create(
            runner, PLUGIN_UUID, GOSSIP_LENGTH, MAX_GOSSIP_COUNT_PER_MESSAGE, getAddrs,
            GossipRecvedEvent, GossipDeletedByGcEvent,
            syncIntervalSeconds=0.1, gossipTTLSeconds=10
        )
        gossiper2 = await Gossiper.create(
            runner2, PLUGIN_UUID, GOSSIP_LENGTH, MAX_GOSSIP_COUNT_PER_MESSAGE, getAddrs,
            GossipRecvedEvent, GossipDeletedByGcEvent,
            syncIntervalSeconds=1, gossipTTLSeconds=10
        )
        
        await runner2.begin()
        await gossiper2.begin()
        
        await gossiper2.addGossip(gossipContent, (await getAddrs())[0])

        assert await gossiper._gossipBytesToFoundTimesAndAddrs.len() == 0
        assert not len(l)

        await asyncio.sleep(0.3)

        assert len(l) == 0

        await runner.end()
        await gossiper2.end()
        await runner2.end()