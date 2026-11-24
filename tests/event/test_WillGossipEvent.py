from P4PCore.plugin.base.gossiper.event.WillGossipEvent import WillGossipEvent


class TestWillGossipEvent:
    def testWillGossipEventStoresGossipContentAndRecipient(self):
        gossipContent = b"gossip"
        recipient = ("127.0.0.1", 12345)

        event = WillGossipEvent(gossipContent, recipient)

        assert not event.isAsync()
        assert event.gossipContent == gossipContent
        assert event.to == recipient
        assert not event.canceled

    def testWillGossipEventCanReplaceContentAndCancelGossip(self):
        event = WillGossipEvent(b"original", ("127.0.0.1", 12345))

        event.gossipContent = b"updated"
        event.cancel()

        assert event.gossipContent == b"updated"
        assert event.canceled
