import pytest

from P4PCore.plugin.append.nodeGossiper.util.NodeIdentifyConverter import nodeIdentifyToBytes, bytesToNodeIdentify
from P4PCore.common.model.NodeIdentify import NodeIdentify
from P4PCore.common.model.HashableEd25519PublicKey import HashableEd25519PublicKey
from P4PCore.plugin.append.nodeGossiper.protocol.Protocol import NodeGossiperPacketElementSize


class TestNodeIdentifyCodec:
    @pytest.mark.asyncio
    async def testNodeIdentifyToBytesSenderInfo(self):
        pubKeyBytes = b"\x01" * 32
        pubKey = HashableEd25519PublicKey(pubKeyBytes)
        nodeIdentify = NodeIdentify(ip="", port=0, hashableEd25519PublicKey=pubKey)

        resultBytes = nodeIdentifyToBytes(nodeIdentify)

        expectedPrefixSize = (
            NodeGossiperPacketElementSize.IP_ADDR_FAMILY
            + NodeGossiperPacketElementSize.IP
            + NodeGossiperPacketElementSize.PORT
        )
        assert resultBytes[:expectedPrefixSize] == b"\x00" * expectedPrefixSize
        assert resultBytes[expectedPrefixSize:] == pubKeyBytes

    @pytest.mark.asyncio
    async def testNodeIdentifyToBytesIPv4(self):
        pubKeyBytes = b"\x02" * 32
        pubKey = HashableEd25519PublicKey(pubKeyBytes)
        nodeIdentify = NodeIdentify(ip="192.168.1.10", port=8080, hashableEd25519PublicKey=pubKey)

        resultBytes = nodeIdentifyToBytes(nodeIdentify)
        
        recovered = bytesToNodeIdentify(resultBytes)
        assert recovered is not None
        assert recovered.ip == "192.168.1.10"
        assert recovered.port == 8080
        assert recovered.hashableEd25519PublicKey.publicKeyBytes == pubKeyBytes

    @pytest.mark.asyncio
    async def testNodeIdentifyToBytesIPv6(self):
        pubKeyBytes = b"\x03" * 32
        pubKey = HashableEd25519PublicKey(pubKeyBytes)
        nodeIdentify = NodeIdentify(ip="2001:db8::1", port=9090, hashableEd25519PublicKey=pubKey)

        resultBytes = nodeIdentifyToBytes(nodeIdentify)

        recovered = bytesToNodeIdentify(resultBytes)
        assert recovered is not None
        assert recovered.ip == "2001:db8::1"
        assert recovered.port == 9090
        assert recovered.hashableEd25519PublicKey.publicKeyBytes == pubKeyBytes

    @pytest.mark.asyncio
    async def testBytesToNodeIdentifySenderInfo(self):
        pubKeyBytes = b"\x04" * 32
        expectedPrefixSize = (
            NodeGossiperPacketElementSize.IP_ADDR_FAMILY
            + NodeGossiperPacketElementSize.IP
            + NodeGossiperPacketElementSize.PORT
        )
        dummyBytes = b"\x00" * expectedPrefixSize + pubKeyBytes

        nodeIdentify = bytesToNodeIdentify(dummyBytes)
        assert nodeIdentify is not None
        assert nodeIdentify.ip == ""
        assert nodeIdentify.port == 0
        assert nodeIdentify.hashableEd25519PublicKey.publicKeyBytes == pubKeyBytes

    @pytest.mark.asyncio
    async def testBytesToNodeIdentifyInvalidFamily(self):
        invalidAddrFamilyB = (99).to_bytes(NodeGossiperPacketElementSize.IP_ADDR_FAMILY, "big")
        ipB = b"\x00" * NodeGossiperPacketElementSize.IP
        portB = (8080).to_bytes(NodeGossiperPacketElementSize.PORT, "big")
        pubKeyBytes = b"\x05" * 32

        invalidBytes = invalidAddrFamilyB + ipB + portB + pubKeyBytes

        result = bytesToNodeIdentify(invalidBytes)
        assert result is None