import os
import pytest

from P4PCore.core.abstract.NetHandler import NetHandler
from P4PCore.core.UserNet import UserNet

FLAG_SIZE = 16

class DummyNetHandler(NetHandler):
    def __init__(self):
        self.handledData: list[tuple[bytes, tuple[str, int]]] = []

    async def handle(self, data: bytes, addr: tuple[str, int]) -> None:
        self.handledData.append((data, addr))

class TestUserNet:
    @pytest.mark.asyncio
    async def testRegisterAndDispatch(self):
        userNet = UserNet(FLAG_SIZE)

        flagA = os.urandom(FLAG_SIZE)
        flagB = os.urandom(FLAG_SIZE)

        handlerA = DummyNetHandler()
        handlerB = DummyNetHandler()

        assert userNet.registerHandler(flagA, handlerA) is True
        assert userNet.registerHandler(flagB, handlerB) is True

        addr = ("127.0.0.1", 12345)
        payloadA = b"hello handler A"
        payloadB = b"hello handler B"

        await userNet.handle(flagA + payloadA, addr)
        await userNet.handle(flagB + payloadB, addr)

        assert len(handlerA.handledData) == 1
        assert handlerA.handledData[0] == (payloadA, addr)

        assert len(handlerB.handledData) == 1
        assert handlerB.handledData[0] == (payloadB, addr)

    def testCannotOverwriteRegister(self):
        userNet = UserNet(FLAG_SIZE)

        flag = os.urandom(FLAG_SIZE)
        handler1 = DummyNetHandler()
        handler2 = DummyNetHandler()

        assert userNet.registerHandler(flag, handler1) is True

        assert userNet.registerHandler(flag, handler2) is False

    @pytest.mark.asyncio
    async def testHandleDataTooShort(self):
        userNet = UserNet(FLAG_SIZE)

        flag = os.urandom(FLAG_SIZE)
        handler = DummyNetHandler()
        userNet.registerHandler(flag, handler)

        addr = ("127.0.0.1", 12345)
        shortData = b"short"

        await userNet.handle(shortData, addr)

        assert len(handler.handledData) == 0

    @pytest.mark.asyncio
    async def testHandleUnregisteredFlag(self):
        userNet = UserNet(FLAG_SIZE)

        flagRegistered = os.urandom(FLAG_SIZE)
        flagUnregistered = os.urandom(FLAG_SIZE)

        handler = DummyNetHandler()
        userNet.registerHandler(flagRegistered, handler)

        addr = ("127.0.0.1", 12345)
        await userNet.handle(flagUnregistered + b"some data", addr)

        assert len(handler.handledData) == 0

    @pytest.mark.asyncio
    async def testDeleteHandler(self):
        userNet = UserNet(FLAG_SIZE)

        flag = os.urandom(FLAG_SIZE)
        handler = DummyNetHandler()

        assert userNet.registerHandler(flag, handler) is True
        assert userNet.deleteHandler(flag) is handler

        addr = ("127.0.0.1", 12345)
        await userNet.handle(flag + b"some data", addr)

        assert len(handler.handledData) == 0