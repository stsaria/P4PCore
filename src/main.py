import asyncio

from src.P4PRunner import P4PRunner
from src.PeerForPeers import PeerForPeers
from src.event.CalledMainEvent import CalledMainEvent
from src.protocol.ProgramProtocol import *

async def amain():
    await asyncio.sleep(0)
    await PeerForPeers.getEventsManager().triggerEvent(CalledMainEvent())
    P4PRunner()

if __name__ == "__main__":
    asyncio.run(amain())