from P4PCore.core.protocol.Protocol import SecurePacketElementSize

class NodeGossiperPacketElementSize(SecurePacketElementSize):
    IP_ADDR_FAMILY = 1
    IPV4 = 4
    IPV6 = 16
    IP = max(IPV4, IPV6)
    PORT = 2

GOSSIP_SIZE = (
    NodeGossiperPacketElementSize.IP_ADDR_FAMILY
    +NodeGossiperPacketElementSize.IP
    +NodeGossiperPacketElementSize.PORT
    +SecurePacketElementSize.ED25519_PUBLIC_KEY
)

MAXIMUM_GOSSIP_COUNT_PER_MESSAGE = 5