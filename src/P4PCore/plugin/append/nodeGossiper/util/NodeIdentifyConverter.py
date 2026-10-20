import socket
from socket import AF_INET6, AF_INET

from P4PCore.common.model.HashableEd25519PublicKey import HashableEd25519PublicKey
from P4PCore.common.util.BytesCoverter import *
from P4PCore.common.model.NodeIdentify import NodeIdentify
from P4PCore.common.util import BytesSplitter
from P4PCore.plugin.append.nodeGossiper.protocol.Protocol import NodeGossiperPacketElementSize

def nodeIdentifyToBytes(nodeIdentify:NodeIdentify) -> bytes:
    """
    Convert a NodeIdentify object to its bytes representation.

    If the NodeIdentify represents the sender's information, its IP address
    should be an empty string and its port should be 0.

    :param nodeIdentify: The NodeIdentify object to convert.
    :return: The bytes representation of the NodeIdentify.
    """

    if not (nodeIdentify.ip and nodeIdentify.port):
        # sender's info
        return (
            b"\x00" * (
                NodeGossiperPacketElementSize.IP_ADDR_FAMILY
                + NodeGossiperPacketElementSize.IP
                + NodeGossiperPacketElementSize.PORT
            )
            + nodeIdentify.hashableEd25519PublicKey.publicKeyBytes
        )

    addrFamilyB = itob(
        addrFamily := (
            AF_INET6 if ":" in (ip := nodeIdentify.ip) else AF_INET
        ),
        NodeGossiperPacketElementSize.IP_ADDR_FAMILY
    )

    ipB = socket.inet_pton(addrFamily, ip)

    return (
        addrFamilyB
        + ipB
        + b"\x00" * (NodeGossiperPacketElementSize.IP - len(ipB))
        + itob(nodeIdentify.port, NodeGossiperPacketElementSize.PORT)
        + nodeIdentify.hashableEd25519PublicKey.publicKeyBytes
    )


def bytesToNodeIdentify(nodeIdentifyB:bytes) -> NodeIdentify | None:
    """
    Convert a bytes representation to a NodeIdentify object.

    If the bytes represent the sender's information, the returned
    NodeIdentify will have an empty IP address and port 0.

    :param nodeIdentifyB: The bytes representation of the NodeIdentify.
    :return: A NodeIdentify object, or None if the address family is invalid.
    """

    addrFamillyB, ipB, portB, pubKeyB = BytesSplitter.split(
        nodeIdentifyB,
        NodeGossiperPacketElementSize.IP_ADDR_FAMILY,
        NodeGossiperPacketElementSize.IP,
        NodeGossiperPacketElementSize.PORT,
        NodeGossiperPacketElementSize.ED25519_PUBLIC_KEY
    )

    if not int.from_bytes(addrFamillyB) + int.from_bytes(ipB) + int.from_bytes(portB):
        # sender's info
        return NodeIdentify(
            ip="",
            port=0,
            hashableEd25519PublicKey=HashableEd25519PublicKey(pubKeyB)
        )

    addrFamilly = btoi(addrFamillyB)

    if addrFamilly == AF_INET:
        ipSize = NodeGossiperPacketElementSize.IPV4
    elif addrFamilly == AF_INET6:
        ipSize = NodeGossiperPacketElementSize.IPV6
    else:
        return

    ip = socket.inet_ntop(addrFamilly, ipB[:ipSize])
    port = btoi(portB)
    pubKey = HashableEd25519PublicKey(pubKeyB)

    return NodeIdentify(
        ip=ip,
        port=port,
        hashableEd25519PublicKey=pubKey
    )