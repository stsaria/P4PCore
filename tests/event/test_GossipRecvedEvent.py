import asyncio
import os
from uuid import uuid4
import pytest

from P4PCore.P4PRunner import P4PRunner
from P4PCore.plugin.base.gossiper.Gossiper import Gossiper
from P4PCore.plugin.base.gossiper.event.GossipRecvedEvent import GossipRecvedEvent
from P4PCore.common.manager.Events import EventListener

PLUGIN_UUID = uuid4()
GOSSIP_LENGTH = 10
MAX_GOSSIP_COUNT_PER_MESSAGE = 10

class TestGossipRecvedEvent:
    @pytest.mark.asyncio
    async def testGossipRecvedEventTriggered(self):
        runner = P4PRunner()
        runner2 = P4PRunner()

        gossiper = Gossiper(
            runner, PLUGIN_UUID, GOSSIP_LENGTH, MAX_GOSSIP_COUNT_PER_MESSAGE,
            lambda:None, GossipRecvedEvent
        )
        gossiper2 = Gossiper(
            runner2, PLUGIN_UUID, GOSSIP_LENGTH, MAX_GOSSIP_COUNT_PER_MESSAGE,
            lambda:None, GossipRecvedEvent
        )

        await runner.begin()
        await runner2.begin()

        receiveds: list[GossipRecvedEvent] = []

        class GossipRecvedListner:
            @EventListener
            async def onRecved(self, e:GossipRecvedEvent):
                receiveds.append(e)

        runner.eventsManager.registerListener(GossipRecvedListner())

        gossipContent = os.urandom(GOSSIP_LENGTH)
        gossiper2._gossip(runner._net._protocolV4.transport.get_extra_info("sockname"), gossipContent)

        await asyncio.sleep(0.1)

        assert len(receiveds) == 1
        assert receiveds[0].gossipContent == gossipContent

        await gossiper.end()
        await runner.end()
        await gossiper2.end()
        await runner2.end()