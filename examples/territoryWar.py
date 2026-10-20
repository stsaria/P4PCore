import argparse
import asyncio
import ipaddress
import secrets
import struct
import time
from collections.abc import Sequence
from random import Random
from uuid import UUID

from P4PCore.P4PRunner import P4PRunner
from P4PCore.common.manager.Events import EventListener
from P4PCore.plugin.append.nodeGossiper.NodeGossiper import NodeGossiper
from P4PCore.plugin.base.gossiper.Gossiper import Gossiper
from P4PCore.plugin.base.gossiper.event.GossipRecvedEvent import GossipRecvedEvent


BOARD_WIDTH = 48
BOARD_HEIGHT = 30
CELL_COUNT = BOARD_WIDTH * BOARD_HEIGHT
BITMAP_SIZE = (CELL_COUNT + 7) // 8
CLAIM_FORMAT = "!8sIH"
CLAIM_SIZE = struct.calcsize(CLAIM_FORMAT)
TEAM_FORMAT = "!8sIB16sB16sH"
TEAM_SIZE = struct.calcsize(TEAM_FORMAT)
SNAPSHOT_FORMAT = f"!8sI{BITMAP_SIZE}s"
SNAPSHOT_SIZE = struct.calcsize(SNAPSHOT_FORMAT)
SNAPSHOT_REQUEST_FORMAT = "!8sI"
SNAPSHOT_REQUEST_SIZE = struct.calcsize(SNAPSHOT_REQUEST_FORMAT)
CLAIM_GOSSIP_UUID = UUID("8f8786a9-daea-40aa-b47f-5b925a5135fb")
TEAM_GOSSIP_UUID = UUID("52b2082e-c858-41eb-92e5-c7cf9bc58ac3")
SNAPSHOT_GOSSIP_UUID = UUID("a971aac9-8ba8-4a85-84e6-e59b74fe8a18")
SNAPSHOT_REQUEST_GOSSIP_UUID = UUID("13dad8af-0b19-4b7b-a226-55936297310e")
HEARTBEAT_TIMEOUT_SECONDS = 8
SNAPSHOT_INTERVAL_SECONDS = 2
GOSSIP_TTL_SECONDS = 12
DEFAULT_PORT = 47474


class TerritoryClaimRecvedEvent(GossipRecvedEvent):
    pass


class TerritoryTeamRecvedEvent(GossipRecvedEvent):
    pass


class TerritorySnapshotRecvedEvent(GossipRecvedEvent):
    pass


class TerritorySnapshotRequestRecvedEvent(GossipRecvedEvent):
    pass


def parseBootstrapNode(value:str) -> tuple[str, int]:
    host, separator, portText = value.rpartition(":")
    if not separator or not host:
        raise argparse.ArgumentTypeError("Expected HOST:PORT")
    try:
        port = int(portText)
    except ValueError as error:
        raise argparse.ArgumentTypeError("PORT must be an integer") from error
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("PORT must be between 1 and 65535")
    return host, port


def encodeClaim(workerId:bytes, sequence:int, cellIndex:int) -> bytes:
    if len(workerId) != 8:
        raise ValueError("workerId must be 8 bytes")
    if not 0 <= sequence <= 0xFFFFFFFF:
        raise ValueError("sequence must fit in 4 bytes")
    if not 0 <= cellIndex < CELL_COUNT:
        raise ValueError("cellIndex is outside the board")
    return struct.pack(CLAIM_FORMAT, workerId, sequence, cellIndex)


def decodeClaim(data:bytes) -> tuple[bytes, int, int]:
    if len(data) != CLAIM_SIZE:
        raise ValueError(f"claim must be {CLAIM_SIZE} bytes")
    workerId, sequence, cellIndex = struct.unpack(CLAIM_FORMAT, data)
    if cellIndex >= CELL_COUNT:
        raise ValueError("cellIndex is outside the board")
    return workerId, sequence, cellIndex


def encodeTeam(
    workerId:bytes,
    counter:int,
    strength:int,
    name:str,
    address:str,
    port:int,
) -> bytes:
    if len(workerId) != 8:
        raise ValueError("workerId must be 8 bytes")
    if not 0 <= counter <= 0xFFFFFFFF:
        raise ValueError("counter must fit in 4 bytes")
    if not 1 <= strength <= 255:
        raise ValueError("strength must be between 1 and 255")
    nameBytes = name.encode("utf-8")
    if not nameBytes or len(nameBytes) > 16:
        raise ValueError("team name must contain 1 to 16 UTF-8 bytes")
    if not 1 <= port <= 65535:
        raise ValueError("port must be between 1 and 65535")
    ipAddress = ipaddress.ip_address(address)
    return struct.pack(
        TEAM_FORMAT,
        workerId,
        counter,
        strength,
        nameBytes.ljust(16, b"\0"),
        ipAddress.version,
        ipAddress.packed.ljust(16, b"\0"),
        port,
    )


def decodeTeam(data:bytes) -> tuple[bytes, int, int, str, str, int]:
    if len(data) != TEAM_SIZE:
        raise ValueError(f"team announcement must be {TEAM_SIZE} bytes")
    workerId, counter, strength, nameBytes, ipVersion, packedAddress, port = (
        struct.unpack(TEAM_FORMAT, data)
    )
    if not strength or ipVersion not in (4, 6) or not port:
        raise ValueError("team announcement contains invalid metadata")
    addressSize = 4 if ipVersion == 4 else 16
    try:
        name = nameBytes.rstrip(b"\0").decode("utf-8")
        address = str(ipaddress.ip_address(packedAddress[:addressSize]))
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError("team announcement contains invalid text or address") from error
    if not name:
        raise ValueError("team name must not be empty")
    return workerId, counter, strength, name, address, port


def encodeSnapshot(workerId:bytes, counter:int, cells:set[int]) -> bytes:
    if len(workerId) != 8:
        raise ValueError("workerId must be 8 bytes")
    if not 0 <= counter <= 0xFFFFFFFF:
        raise ValueError("counter must fit in 4 bytes")
    bitmap = bytearray(BITMAP_SIZE)
    for cellIndex in cells:
        if not 0 <= cellIndex < CELL_COUNT:
            raise ValueError("cell index is outside the board")
        bitmap[cellIndex // 8] |= 1 << (cellIndex % 8)
    return struct.pack(SNAPSHOT_FORMAT, workerId, counter, bytes(bitmap))


def decodeSnapshot(data:bytes) -> tuple[bytes, int, set[int]]:
    if len(data) != SNAPSHOT_SIZE:
        raise ValueError(f"territory snapshot must be {SNAPSHOT_SIZE} bytes")
    workerId, counter, bitmap = struct.unpack(SNAPSHOT_FORMAT, data)
    cells = {
        cellIndex
        for cellIndex in range(CELL_COUNT)
        if bitmap[cellIndex // 8] & (1 << (cellIndex % 8))
    }
    return workerId, counter, cells


def getAdjacentCells(cellIndex:int) -> set[int]:
    x = cellIndex % BOARD_WIDTH
    y = cellIndex // BOARD_WIDTH
    adjacent = set()
    if x:
        adjacent.add(cellIndex - 1)
    if x + 1 < BOARD_WIDTH:
        adjacent.add(cellIndex + 1)
    if y:
        adjacent.add(cellIndex - BOARD_WIDTH)
    if y + 1 < BOARD_HEIGHT:
        adjacent.add(cellIndex + BOARD_WIDTH)
    return adjacent


def connectedComponents(cells:set[int]) -> list[set[int]]:
    remaining = set(cells)
    components = []
    while remaining:
        start = remaining.pop()
        component = {start}
        frontier = [start]
        while frontier:
            for adjacent in getAdjacentCells(frontier.pop()):
                if adjacent in remaining:
                    remaining.remove(adjacent)
                    component.add(adjacent)
                    frontier.append(adjacent)
        components.append(component)
    return sorted(components, key=min)


def isConnectedTerritory(cells:set[int]) -> bool:
    return len(connectedComponents(cells)) <= 1


def canClaimCell(board:list[bytes | None], ownerId:bytes, cellIndex:int) -> bool:
    currentOwner = board[cellIndex]
    if currentOwner == ownerId:
        return False
    if not any(board[adjacent] == ownerId for adjacent in getAdjacentCells(cellIndex)):
        return False
    if currentOwner is None:
        return True
    remainingVictimCells = {
        index
        for index, owner in enumerate(board)
        if owner == currentOwner and index != cellIndex
    }
    return isConnectedTerritory(remainingVictimCells)


def encodeSnapshotRequest(viewerId:bytes, counter:int) -> bytes:
    if len(viewerId) != 8:
        raise ValueError("viewerId must be 8 bytes")
    if not 0 <= counter <= 0xFFFFFFFF:
        raise ValueError("counter must fit in 4 bytes")
    return struct.pack(SNAPSHOT_REQUEST_FORMAT, viewerId, counter)


def decodeSnapshotRequest(data:bytes) -> tuple[bytes, int]:
    if len(data) != SNAPSHOT_REQUEST_SIZE:
        raise ValueError(f"snapshot request must be {SNAPSHOT_REQUEST_SIZE} bytes")
    return struct.unpack(SNAPSHOT_REQUEST_FORMAT, data)


def createParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one P2P territory team. Launch it once per team."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Address to bind")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="UDP port")
    parser.add_argument(
        "--advertise-host",
        help="LAN-reachable IP address announced to other nodes",
    )
    parser.add_argument("--name", default="Team", help="Team name (up to 16 UTF-8 bytes)")
    parser.add_argument(
        "--strength",
        type=int,
        default=1,
        help="Expansion strength (1-255; stronger teams claim more often)",
    )
    parser.add_argument(
        "--minutes",
        type=float,
        default=30,
        help="How long this node plays before exiting (default: 30 minutes)",
    )
    parser.add_argument(
        "--bootstrap",
        action="append",
        type=parseBootstrapNode,
        default=[],
        metavar="HOST:PORT",
        help="Peer to join; repeat for multiple bootstrap nodes",
    )
    return parser


def createPeerAddressGetter(nodeGossiper:NodeGossiper):
    async def getPeerAddrs() -> set[tuple[str, int]]:
        return await nodeGossiper.getAddrs()

    return getPeerAddrs


async def runTeam(
    host:str,
    port:int,
    advertiseHost:str,
    teamName:str,
    strength:int,
    durationMinutes:float,
    bootstrapNodes:set[tuple[str, int]],
) -> None:
    runner = P4PRunner(netV4ListeningAddr=(host, port))
    nodeGossiper = NodeGossiper(
        runner,
        syncIntervalSeconds=0.5,
        bootstrapNodes=bootstrapNodes,
    )
    workerId = secrets.token_bytes(8)
    board:list[bytes | None] = [None] * CELL_COUNT
    versions:list[tuple[int, bytes]] = [(-1, b"")] * CELL_COUNT
    workers:dict[bytes, dict[str, int | str]] = {
        workerId: {
            "name": teamName,
            "strength": strength,
            "address": advertiseHost,
            "port": port,
        }
    }
    lastSeen = {workerId: time.monotonic()}
    heartbeatCounters:dict[bytes, int] = {workerId: 0}
    latestHeartbeats:dict[bytes, bytes] = {}
    deadWorkers:set[bytes] = set()
    sequence = 0
    snapshotCounters:dict[bytes, int] = {}
    startedAt = time.monotonic()
    endsAt = startedAt + durationMinutes * 60
    stopEvent = asyncio.Event()
    tasks:list[asyncio.Task] = []
    gossipers:list[Gossiper] = []
    runnerStarted = False
    state = "running"

    try:
        await runner.begin()
        runnerStarted = True
        await nodeGossiper.begin()
        getPeerAddrs = createPeerAddressGetter(nodeGossiper)
        claimGossiper = Gossiper(
            runner,
            CLAIM_GOSSIP_UUID,
            CLAIM_SIZE,
            5,
            getPeerAddrs,
            TerritoryClaimRecvedEvent,
            syncIntervalSeconds=0.2,
            gossipTTLSeconds=GOSSIP_TTL_SECONDS,
            maximumSavedDataCount=10_000,
            minimumSavedDataCount=0,
        )
        teamGossiper = Gossiper(
            runner,
            TEAM_GOSSIP_UUID,
            TEAM_SIZE,
            1,
            getPeerAddrs,
            TerritoryTeamRecvedEvent,
            syncIntervalSeconds=0.25,
            gossipTTLSeconds=10,
            maximumSavedDataCount=10_000,
            minimumSavedDataCount=0,
        )
        snapshotGossiper = Gossiper(
            runner,
            SNAPSHOT_GOSSIP_UUID,
            SNAPSHOT_SIZE,
            1,
            getPeerAddrs,
            TerritorySnapshotRecvedEvent,
            syncIntervalSeconds=0.2,
            gossipTTLSeconds=GOSSIP_TTL_SECONDS,
            maximumSavedDataCount=10_000,
            minimumSavedDataCount=0,
        )
        snapshotRequestGossiper = Gossiper(
            runner,
            SNAPSHOT_REQUEST_GOSSIP_UUID,
            SNAPSHOT_REQUEST_SIZE,
            5,
            getPeerAddrs,
            TerritorySnapshotRequestRecvedEvent,
            syncIntervalSeconds=0.25,
            gossipTTLSeconds=12,
            maximumSavedDataCount=1_000,
            minimumSavedDataCount=0,
        )
        gossipers = [
            claimGossiper,
            teamGossiper,
            snapshotGossiper,
            snapshotRequestGossiper,
        ]
        snapshotCounter = [0]
        previousSnapshot:bytes | None = None

        def publishSnapshot() -> None:
            nonlocal previousSnapshot
            snapshotCounter[0] = (snapshotCounter[0] + 1) & 0xFFFFFFFF
            if previousSnapshot is not None:
                snapshotGossiper.deleteGossip(previousSnapshot)
            cells = {
                cellIndex
                for cellIndex, ownerId in enumerate(board)
                if ownerId == workerId
            }
            previousSnapshot = encodeSnapshot(
                workerId,
                snapshotCounter[0],
                cells,
            )
            snapshotGossiper.addGossip(previousSnapshot)

        class ClaimListener:
            @EventListener
            async def onClaim(self, event:TerritoryClaimRecvedEvent) -> None:
                try:
                    ownerId, ownerSequence, cellIndex = decodeClaim(event.gossipContent)
                except ValueError as error:
                    print(f"Ignored invalid territory claim: {error}")
                    return
                if ownerId not in workers:
                    workers[ownerId] = {
                        "name": f"Team {ownerId.hex()[:4]}",
                        "strength": 1,
                        "address": event.addr[0],
                        "port": event.addr[1],
                    }
                if ownerId in deadWorkers:
                    return
                version = (ownerSequence, ownerId)
                if (
                    version > versions[cellIndex]
                    and canClaimCell(board, ownerId, cellIndex)
                ):
                    board[cellIndex] = ownerId
                    versions[cellIndex] = version
                claimGossiper.addGossip(event.gossipContent, event.addr)

        class TeamListener:
            @EventListener
            async def onTeam(self, event:TerritoryTeamRecvedEvent) -> None:
                try:
                    (
                        ownerId,
                        counter,
                        ownerStrength,
                        ownerName,
                        ownerAddress,
                        ownerPort,
                    ) = decodeTeam(event.gossipContent)
                except ValueError as error:
                    print(f"Ignored invalid team announcement: {error}")
                    return
                if counter <= heartbeatCounters.get(ownerId, -1):
                    return
                previous = latestHeartbeats.get(ownerId)
                if previous is not None:
                    teamGossiper.deleteGossip(previous)
                latestHeartbeats[ownerId] = event.gossipContent
                heartbeatCounters[ownerId] = counter
                workers[ownerId] = {
                    "name": ownerName,
                    "strength": ownerStrength,
                    "address": ownerAddress,
                    "port": ownerPort,
                }
                lastSeen[ownerId] = time.monotonic()
                deadWorkers.discard(ownerId)
                teamGossiper.addGossip(event.gossipContent, event.addr)

        class SnapshotListener:
            @EventListener
            async def onSnapshot(self, event:TerritorySnapshotRecvedEvent) -> None:
                try:
                    ownerId, counter, cells = decodeSnapshot(event.gossipContent)
                except ValueError as error:
                    print(f"Ignored invalid territory snapshot: {error}")
                    return
                if ownerId not in workers or ownerId in deadWorkers:
                    return
                if counter <= snapshotCounters.get(ownerId, -1):
                    return
                if not isConnectedTerritory(cells):
                    return
                updatedBoard = [
                    None if currentOwner == ownerId else currentOwner
                    for currentOwner in board
                ]
                for cellIndex in cells:
                    if updatedBoard[cellIndex] is None:
                        updatedBoard[cellIndex] = ownerId
                updatedCells = {
                    cellIndex
                    for cellIndex, currentOwner in enumerate(updatedBoard)
                    if currentOwner == ownerId
                }
                if not isConnectedTerritory(updatedCells):
                    return
                snapshotCounters[ownerId] = counter
                previousBoard = board.copy()
                board[:] = updatedBoard
                for cellIndex, currentOwner in enumerate(board):
                    if (
                        currentOwner == ownerId
                        and previousBoard[cellIndex] is None
                    ):
                        versions[cellIndex] = (0, ownerId)
                snapshotGossiper.addGossip(event.gossipContent, event.addr)

        class SnapshotRequestListener:
            @EventListener
            async def onSnapshotRequest(
                self,
                event:TerritorySnapshotRequestRecvedEvent,
            ) -> None:
                try:
                    decodeSnapshotRequest(event.gossipContent)
                except ValueError as error:
                    print(f"Ignored invalid territory query: {error}")
                    return
                if snapshotRequestGossiper.addGossip(
                    event.gossipContent,
                    event.addr,
                ):
                    publishSnapshot()

        runner.eventsManager.registerListener(ClaimListener())
        runner.eventsManager.registerListener(TeamListener())
        runner.eventsManager.registerListener(SnapshotListener())
        runner.eventsManager.registerListener(SnapshotRequestListener())
        for gossiper in gossipers:
            await gossiper.begin()

        transport = runner.net._protocolV4.transport
        if transport is None:
            raise RuntimeError("Node failed to open its IPv4 socket")
        actualPort = int(transport.get_extra_info("sockname")[1])
        workers[workerId]["port"] = actualPort
        if advertiseHost in ("0.0.0.0", "::"):
            raise ValueError("--advertise-host must be a reachable LAN IP address")

        seedCell = int.from_bytes(workerId[:4], "big") % CELL_COUNT
        board[seedCell] = workerId
        versions[seedCell] = (0, workerId)
        claimGossiper.addGossip(encodeClaim(workerId, 0, seedCell))
        publishSnapshot()

        async def publishTeamInfo() -> None:
            counter = 0
            previous:bytes | None = None
            while not stopEvent.is_set():
                counter = (counter + 1) & 0xFFFFFFFF
                if previous is not None:
                    teamGossiper.deleteGossip(previous)
                previous = encodeTeam(
                    workerId,
                    counter,
                    strength,
                    teamName,
                    advertiseHost,
                    actualPort,
                )
                teamGossiper.addGossip(previous)
                lastSeen[workerId] = time.monotonic()
                await asyncio.sleep(0.5)

        async def publishTerritory() -> None:
            while not stopEvent.is_set():
                publishSnapshot()
                await asyncio.sleep(SNAPSHOT_INTERVAL_SECONDS)

        async def clearDisconnectedTeams() -> None:
            while not stopEvent.is_set():
                now = time.monotonic()
                for ownerId, seenAt in list(lastSeen.items()):
                    if ownerId == workerId or ownerId in deadWorkers:
                        continue
                    if now - seenAt > HEARTBEAT_TIMEOUT_SECONDS:
                        deadWorkers.add(ownerId)
                        for cellIndex, currentOwner in enumerate(board):
                            if currentOwner == ownerId:
                                board[cellIndex] = None
                                versions[cellIndex] = (-1, b"")
                await asyncio.sleep(0.5)

        async def expandTerritory() -> None:
            nonlocal sequence
            random = Random(workerId)
            while not stopEvent.is_set() and time.monotonic() < endsAt:
                frontier:set[int] = set()
                for cellIndex, ownerId in enumerate(board):
                    if ownerId != workerId:
                        continue
                    frontier.update(getAdjacentCells(cellIndex))
                frontier = {
                    cellIndex
                    for cellIndex in frontier
                    if canClaimCell(board, workerId, cellIndex)
                }
                for _ in range(strength):
                    if not frontier:
                        break
                    cellIndex = random.choice(tuple(frontier))
                    frontier.discard(cellIndex)
                    sequence += 1
                    if sequence > 0xFFFFFFFF:
                        sequence = 1
                    claim = encodeClaim(workerId, sequence, cellIndex)
                    version = (sequence, workerId)
                    if (
                        version > versions[cellIndex]
                        and canClaimCell(board, workerId, cellIndex)
                    ):
                        board[cellIndex] = workerId
                        versions[cellIndex] = version
                        claimGossiper.addGossip(claim)
                await asyncio.sleep(0.25)
            stopEvent.set()

        print(f"{teamName} [{workerId.hex()[:8]}] listening on {host}:{actualPort}")
        print(f"Strength: {strength}; battle duration: {durationMinutes:g} minutes")
        if bootstrapNodes:
            print("Joining through: " + ", ".join(
                f"{peerHost}:{peerPort}" for peerHost, peerPort in sorted(bootstrapNodes)
            ))
        else:
            print("This is the seed node. Other teams and the viewer should bootstrap here.")

        tasks = [
            asyncio.create_task(publishTeamInfo()),
            asyncio.create_task(publishTerritory()),
            asyncio.create_task(clearDisconnectedTeams()),
            asyncio.create_task(expandTerritory()),
        ]
        await asyncio.gather(*tasks)
        state = "complete"
    except asyncio.CancelledError:
        state = "stopped"
        raise
    except Exception:
        state = "error"
        raise
    finally:
        stopEvent.set()
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        for gossiper in gossipers:
            await gossiper.end()
        if runnerStarted:
            await nodeGossiper.end()
            await runner.end()
        print(f"{teamName} stopped ({state})")


async def main(args:Sequence[str] | None=None) -> None:
    options = createParser().parse_args(args)
    if not 1 <= options.port <= 65535:
        raise SystemExit("--port must be between 1 and 65535")
    if not 1 <= options.strength <= 255:
        raise SystemExit("--strength must be between 1 and 255")
    if options.minutes <= 0:
        raise SystemExit("--minutes must be greater than 0")
    try:
        if not options.name.encode("utf-8") or len(options.name.encode("utf-8")) > 16:
            raise ValueError("Team name must contain 1 to 16 UTF-8 bytes")
    except UnicodeEncodeError as error:
        raise SystemExit(f"Invalid team name: {error}") from error
    advertiseHost = options.advertise_host or options.host
    if advertiseHost in ("0.0.0.0", "::"):
        raise SystemExit(
            "When binding to a wildcard address, set --advertise-host to a reachable LAN IP"
        )
    await runTeam(
        options.host,
        options.port,
        advertiseHost,
        options.name,
        options.strength,
        options.minutes,
        set(options.bootstrap),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
