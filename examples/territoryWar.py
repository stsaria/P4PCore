import argparse
import asyncio
import secrets
import struct
import time
from collections import deque
from collections.abc import Sequence
from random import Random
from uuid import UUID

from P4PCore.P4PRunner import P4PRunner
from P4PCore.common.manager.Events import EventListener
from P4PCore.core.abstract.NetHandler import NetHandler
from P4PCore.plugin.append.nodeGossiper.NodeGossiper import NodeGossiper
from P4PCore.plugin.base.gossiper.Gossiper import Gossiper
from P4PCore.plugin.base.gossiper.event.GossipRecvedEvent import GossipRecvedEvent


BOARD_WIDTH = 128
BOARD_HEIGHT = 84
CELL_COUNT = BOARD_WIDTH * BOARD_HEIGHT
BITMAP_SIZE = (CELL_COUNT + 7) // 8
CLAIM_FORMAT = "!8sIH"
CLAIM_SIZE = struct.calcsize(CLAIM_FORMAT)
TEAM_FORMAT = "!8sIB"
TEAM_SIZE = struct.calcsize(TEAM_FORMAT)
SNAPSHOT_FORMAT = f"!8sI{BITMAP_SIZE}s"
SNAPSHOT_SIZE = struct.calcsize(SNAPSHOT_FORMAT)
SNAPSHOT_REQUEST_FORMAT = "!8sI"
SNAPSHOT_REQUEST_SIZE = struct.calcsize(SNAPSHOT_REQUEST_FORMAT)
CONTROL_FORMAT = "!8sQIB"
CONTROL_SIZE = struct.calcsize(CONTROL_FORMAT)
CLAIM_GOSSIP_UUID = UUID("8f8786a9-daea-40aa-b47f-5b925a5135fb")
TEAM_GOSSIP_UUID = UUID("52b2082e-c858-41eb-92e5-c7cf9bc58ac3")
SNAPSHOT_GOSSIP_UUID = UUID("a971aac9-8ba8-4a85-84e6-e59b74fe8a18")
SNAPSHOT_REQUEST_GOSSIP_UUID = UUID("13dad8af-0b19-4b7b-a226-55936297310e")
CONTROL_UUID = UUID("7c617d85-9c87-4f1e-a4f8-e14e187e5f19")
BATTLE_COMMAND_START = 1
BATTLE_COMMAND_RESET = 2
HEARTBEAT_TIMEOUT_SECONDS = 8
SNAPSHOT_INTERVAL_SECONDS = 0.1
EXPANSION_INTERVAL_SECONDS = 0.7
EXPANSION_CLAIMS_PER_STRENGTH = 2
DISSATISFIED_NEIGHBOR_THRESHOLD = 3
GOSSIP_TTL_SECONDS = 12


class TerritoryClaimRecvedEvent(GossipRecvedEvent):
    pass


class TerritoryTeamRecvedEvent(GossipRecvedEvent):
    pass


class TerritorySnapshotRecvedEvent(GossipRecvedEvent):
    pass


class TerritorySnapshotRequestRecvedEvent(GossipRecvedEvent):
    pass


def createTeamProfile(workerId:bytes) -> tuple[str, int]:
    if len(workerId) != 8:
        raise ValueError("workerId must be 8 bytes")
    return f"Team-{workerId.hex()[:6]}", workerId[0] % 5 + 1


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
    active:bool,
) -> bytes:
    if len(workerId) != 8:
        raise ValueError("workerId must be 8 bytes")
    if not 0 <= counter <= 0xFFFFFFFF:
        raise ValueError("counter must fit in 4 bytes")
    return struct.pack(TEAM_FORMAT, workerId, counter, int(active))


def decodeTeam(data:bytes) -> tuple[bytes, int, bool]:
    if len(data) != TEAM_SIZE:
        raise ValueError(f"team announcement must be {TEAM_SIZE} bytes")
    workerId, counter, active = struct.unpack(TEAM_FORMAT, data)
    if active not in (0, 1):
        raise ValueError("team announcement has invalid activity state")
    return workerId, counter, bool(active)


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


def getEightNeighborCells(cellIndex:int) -> set[int]:
    x = cellIndex % BOARD_WIDTH
    y = cellIndex // BOARD_WIDTH
    return {
        neighborY * BOARD_WIDTH + neighborX
        for neighborY in range(max(0, y - 1), min(BOARD_HEIGHT, y + 2))
        for neighborX in range(max(0, x - 1), min(BOARD_WIDTH, x + 2))
        if (neighborX, neighborY) != (x, y)
    }


def chooseStartingCell(
    board:list[bytes | None],
    random:Random,
) -> int:
    emptyCells = [
        cellIndex
        for cellIndex, ownerId in enumerate(board)
        if ownerId is None
    ]
    if not emptyCells:
        raise ValueError("board has no empty cells")

    distances = [-1] * len(board)
    frontier = deque()
    for cellIndex, ownerId in enumerate(board):
        if ownerId is not None:
            distances[cellIndex] = 0
            frontier.append(cellIndex)

    if not frontier:
        return random.choice(emptyCells)

    while frontier:
        cellIndex = frontier.popleft()
        nextDistance = distances[cellIndex] + 1
        for adjacent in getAdjacentCells(cellIndex):
            if distances[adjacent] == -1:
                distances[adjacent] = nextDistance
                frontier.append(adjacent)

    farthestDistance = max(distances[cellIndex] for cellIndex in emptyCells)
    farthestCells = [
        cellIndex
        for cellIndex in emptyCells
        if distances[cellIndex] == farthestDistance
    ]
    return random.choice(farthestCells)


def countDissatisfiedDirections(
    board:list[bytes | None],
    ownerId:bytes,
    cellIndex:int,
) -> int:
    return sum(
        board[neighbor] != ownerId
        for neighbor in getEightNeighborCells(cellIndex)
    )


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
        return any(
            countDissatisfiedDirections(board, ownerId, adjacent)
            >= DISSATISFIED_NEIGHBOR_THRESHOLD
            for adjacent in getAdjacentCells(cellIndex)
            if board[adjacent] == ownerId
        )
    if (
        countDissatisfiedDirections(board, currentOwner, cellIndex)
        < DISSATISFIED_NEIGHBOR_THRESHOLD
    ):
        return False
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


def encodeControl(
    controllerId:bytes,
    issuedAt:int,
    counter:int,
    command:int,
) -> bytes:
    if len(controllerId) != 8:
        raise ValueError("controllerId must be 8 bytes")
    if not 0 <= issuedAt <= 0xFFFFFFFFFFFFFFFF:
        raise ValueError("issuedAt must fit in 8 bytes")
    if not 0 <= counter <= 0xFFFFFFFF:
        raise ValueError("counter must fit in 4 bytes")
    if command not in (BATTLE_COMMAND_START, BATTLE_COMMAND_RESET):
        raise ValueError("unknown battle command")
    return struct.pack(CONTROL_FORMAT, controllerId, issuedAt, counter, command)


def decodeControl(data:bytes) -> tuple[bytes, int, int, int]:
    if len(data) != CONTROL_SIZE:
        raise ValueError(f"battle control must be {CONTROL_SIZE} bytes")
    controllerId, issuedAt, counter, command = struct.unpack(CONTROL_FORMAT, data)
    if command not in (BATTLE_COMMAND_START, BATTLE_COMMAND_RESET):
        raise ValueError("unknown battle command")
    return controllerId, issuedAt, counter, command


def createParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one P2P territory team. Launch it once per team."
    )
    parser.add_argument("--host", default="0.0.0.0", help="Address to bind")
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
    bootstrapNodes:set[tuple[str, int]],
) -> None:
    runner = P4PRunner(netV4ListeningAddr=(host, 0))
    nodeGossiper = NodeGossiper(
        runner,
        syncIntervalSeconds=0.5,
        bootstrapNodes=bootstrapNodes,
    )
    workerId = secrets.token_bytes(8)
    teamName, strength = createTeamProfile(workerId)
    startingCellRandom = Random(workerId)
    board:list[bytes | None] = [None] * CELL_COUNT
    versions:list[tuple[int, bytes]] = [(-1, b"")] * CELL_COUNT
    workers:dict[bytes, dict[str, int | str | bool]] = {
        workerId: {
            "name": teamName,
            "strength": strength,
            "active": False,
        }
    }
    lastSeen = {workerId: time.monotonic()}
    heartbeatCounters:dict[bytes, int] = {workerId: 0}
    latestHeartbeats:dict[bytes, bytes] = {}
    deadWorkers:set[bytes] = set()
    sequence = 0
    snapshotCounters:dict[bytes, int] = {}
    active = [False]
    latestControlVersion:tuple[int, int, bytes] = (-1, -1, b"")
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
                if not active[0]:
                    return
                if ownerId not in workers:
                    ownerName, ownerStrength = createTeamProfile(ownerId)
                    workers[ownerId] = {
                        "name": ownerName,
                        "strength": ownerStrength,
                        "active": False,
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
                    ownerId, counter, ownerActive = decodeTeam(event.gossipContent)
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
                ownerName, ownerStrength = createTeamProfile(ownerId)
                workers[ownerId] = {
                    "name": ownerName,
                    "strength": ownerStrength,
                    "active": ownerActive,
                }
                lastSeen[ownerId] = time.monotonic()
                deadWorkers.discard(ownerId)
                teamGossiper.addGossip(event.gossipContent, event.addr)

        class ControlHandler(NetHandler):
            async def handle(self, data:bytes, addr:tuple[str, int]) -> None:
                nonlocal latestControlVersion, sequence
                try:
                    controllerId, issuedAt, counter, command = decodeControl(data)
                except ValueError as error:
                    print(f"Ignored invalid direct battle command: {error}")
                    return
                controlVersion = (issuedAt, counter, controllerId)
                if controlVersion <= latestControlVersion:
                    return
                latestControlVersion = controlVersion
                if command == BATTLE_COMMAND_START:
                    if not active[0] and workerId not in board:
                        seedCell = chooseStartingCell(board, startingCellRandom)
                        board[seedCell] = workerId
                        versions[seedCell] = (0, workerId)
                        claimGossiper.addGossip(encodeClaim(workerId, 0, seedCell))
                    active[0] = True
                    workers[workerId]["active"] = True
                    publishSnapshot()
                    return

                active[0] = False
                workers[workerId]["active"] = False
                board[:] = [None] * CELL_COUNT
                versions[:] = [(-1, b"")] * CELL_COUNT
                sequence = 0
                for gossip in claimGossiper.gossips:
                    claimGossiper.deleteGossip(gossip)
                for gossip in snapshotGossiper.gossips:
                    snapshotGossiper.deleteGossip(gossip)
                publishSnapshot()

        class SnapshotListener:
            @EventListener
            async def onSnapshot(self, event:TerritorySnapshotRecvedEvent) -> None:
                try:
                    ownerId, counter, cells = decodeSnapshot(event.gossipContent)
                except ValueError as error:
                    print(f"Ignored invalid territory snapshot: {error}")
                    return
                if not active[0]:
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
        if not runner.userNet.registerHandler(CONTROL_UUID.bytes, ControlHandler()):
            raise RuntimeError("Unable to register the direct battle command handler")
        for gossiper in gossipers:
            await gossiper.begin()

        transport = runner.net._protocolV4.transport
        if transport is None:
            raise RuntimeError("Node failed to open its IPv4 socket")
        actualPort = int(transport.get_extra_info("sockname")[1])

        async def publishTeamInfo() -> None:
            counter = 0
            previous:bytes | None = None
            while not stopEvent.is_set():
                counter = (counter + 1) & 0xFFFFFFFF
                if previous is not None:
                    teamGossiper.deleteGossip(previous)
                previous = encodeTeam(workerId, counter, active[0])
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
                await asyncio.sleep(0.5)

        async def expandTerritory() -> None:
            nonlocal sequence
            random = Random(workerId)
            while not stopEvent.is_set():
                if not active[0]:
                    await asyncio.sleep(0.25)
                    continue
                frontier:set[int] = set()
                for cellIndex, ownerId in enumerate(board):
                    if (
                        ownerId != workerId
                        or countDissatisfiedDirections(board, workerId, cellIndex)
                        < DISSATISFIED_NEIGHBOR_THRESHOLD
                    ):
                        continue
                    frontier.update(getAdjacentCells(cellIndex))
                frontier = {
                    cellIndex
                    for cellIndex in frontier
                    if canClaimCell(board, workerId, cellIndex)
                }
                for _ in range(strength * EXPANSION_CLAIMS_PER_STRENGTH):
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
                await asyncio.sleep(EXPANSION_INTERVAL_SECONDS)
        print(f"{teamName} [{workerId.hex()[:8]}] listening on {host}:{actualPort}")
        print(f"READY {actualPort}", flush=True)
        print(f"Strength: {strength}; waiting for the GUI to start the battle.")
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
    await runTeam(options.host, set(options.bootstrap))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
