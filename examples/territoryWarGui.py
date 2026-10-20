import argparse
import asyncio
import colorsys
import queue
import secrets
import threading
import time
import tkinter as tk
from collections.abc import Sequence
from tkinter import ttk

from P4PCore.P4PRunner import P4PRunner
from P4PCore.common.manager.Events import EventListener
from P4PCore.common.util.BytesCoverter import itob
from P4PCore.core.Net import Net
from P4PCore.core.protocol.Protocol import PacketElementSize, PacketFlag
from P4PCore.plugin.append.nodeGossiper.NodeGossiper import NodeGossiper
from P4PCore.plugin.base.gossiper.Gossiper import Gossiper

if __package__:
    from examples.territoryWar import (
        BOARD_HEIGHT,
        BOARD_WIDTH,
        CLAIM_GOSSIP_UUID,
        CLAIM_SIZE,
        BATTLE_COMMAND_RESET,
        BATTLE_COMMAND_START,
        CONTROL_UUID,
        HEARTBEAT_TIMEOUT_SECONDS,
        SNAPSHOT_GOSSIP_UUID,
        SNAPSHOT_REQUEST_GOSSIP_UUID,
        SNAPSHOT_REQUEST_SIZE,
        SNAPSHOT_SIZE,
        TEAM_GOSSIP_UUID,
        TEAM_SIZE,
        TerritoryClaimRecvedEvent,
        TerritorySnapshotRecvedEvent,
        TerritorySnapshotRequestRecvedEvent,
        TerritoryTeamRecvedEvent,
        createPeerAddressGetter,
        connectedComponents,
        decodeClaim,
        decodeSnapshot,
        decodeSnapshotRequest,
        decodeTeam,
        createTeamProfile,
        encodeControl,
        encodeSnapshotRequest,
        parseBootstrapNode,
    )
else:
    from territoryWar import (
        BOARD_HEIGHT,
        BOARD_WIDTH,
        CLAIM_GOSSIP_UUID,
        CLAIM_SIZE,
        BATTLE_COMMAND_RESET,
        BATTLE_COMMAND_START,
        CONTROL_UUID,
        HEARTBEAT_TIMEOUT_SECONDS,
        SNAPSHOT_GOSSIP_UUID,
        SNAPSHOT_REQUEST_GOSSIP_UUID,
        SNAPSHOT_REQUEST_SIZE,
        SNAPSHOT_SIZE,
        TEAM_GOSSIP_UUID,
        TEAM_SIZE,
        TerritoryClaimRecvedEvent,
        TerritorySnapshotRecvedEvent,
        TerritorySnapshotRequestRecvedEvent,
        TerritoryTeamRecvedEvent,
        createPeerAddressGetter,
        connectedComponents,
        decodeClaim,
        decodeSnapshot,
        decodeSnapshotRequest,
        decodeTeam,
        createTeamProfile,
        encodeControl,
        encodeSnapshotRequest,
        parseBootstrapNode,
    )


BACKGROUND = "#101522"
PANEL = "#1b2435"
TEXT = "#f2f5fa"
MUTED = "#a6b0c2"
NEUTRAL = "#293244"
def createTeamColor(workerId:bytes) -> str:
    hue = int.from_bytes(workerId, "big") / 0xFFFFFFFFFFFFFFFF
    red, green, blue = colorsys.hsv_to_rgb(hue, 0.68, 0.96)
    return f"#{int(red * 255):02x}{int(green * 255):02x}{int(blue * 255):02x}"


def sendDirectBattleCommand(
    net:Net,
    peers:set[tuple[str, int]],
    controllerId:bytes,
    issuedAt:int,
    counter:int,
    command:int,
) -> list[tuple[str, int]]:
    packet = (
        itob(PacketFlag.USER, PacketElementSize.PACKET_FLAG)
        + CONTROL_UUID.bytes
        + encodeControl(controllerId, issuedAt, counter, command)
    )
    return [
        peer
        for peer in sorted(peers)
        if not net.sendTo(packet, peer)
    ]


class TerritoryViewer:
    def __init__(
        self,
        bootstrapNodes:set[tuple[str, int]],
        host:str,
    ):
        self._bootstrapNodes = bootstrapNodes
        self._host = host
        self._lock = threading.Lock()
        self._teams:dict[bytes, dict[str, int | str | bool]] = {}
        self._lastSeen:dict[bytes, float] = {}
        self._heartbeatCounters:dict[bytes, int] = {}
        self._latestHeartbeats:dict[bytes, bytes] = {}
        self._snapshots:dict[bytes, tuple[int, set[int]]] = {}
        self._claims:dict[int, tuple[bytes, int]] = {}
        self._knownNodeCount = 0
        self._error:str | None = None
        self._stopThreadEvent = threading.Event()
        self._loop:asyncio.AbstractEventLoop | None = None
        self._stopAsyncEvent:asyncio.Event | None = None
        self._viewerId = secrets.token_bytes(8)
        self._commands:queue.SimpleQueue[int] = queue.SimpleQueue()
        self._battleStarted = False
        self._thread = threading.Thread(target=self._runThread, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stopThreadEvent.set()
        if self._loop is not None and self._stopAsyncEvent is not None:
            self._loop.call_soon_threadsafe(self._stopAsyncEvent.set)
        if self._thread.is_alive():
            self._thread.join(timeout=3)

    def sendBattleCommand(self, command:int) -> None:
        if command not in (BATTLE_COMMAND_START, BATTLE_COMMAND_RESET):
            raise ValueError("unknown battle command")
        with self._lock:
            self._battleStarted = command == BATTLE_COMMAND_START
            if command == BATTLE_COMMAND_RESET:
                self._snapshots.clear()
                self._claims.clear()
        self._commands.put(command)

    def snapshot(self) -> dict[str, object]:
        now = time.monotonic()
        with self._lock:
            teams = []
            aliveIds:set[bytes] = set()
            for workerId, worker in self._teams.items():
                alive = now - self._lastSeen.get(workerId, 0) < HEARTBEAT_TIMEOUT_SECONDS
                if alive:
                    aliveIds.add(workerId)
                teams.append({
                    **worker,
                    "id": workerId.hex(),
                    "workerId": workerId,
                    "alive": alive,
                    "color": createTeamColor(workerId),
                })
            board = [0] * (BOARD_WIDTH * BOARD_HEIGHT)
            candidates:dict[int, list[tuple[bytes, int]]] = {}
            if self._battleStarted:
                for workerId, (_, cells) in self._snapshots.items():
                    for cellIndex in cells:
                        candidates.setdefault(cellIndex, []).append(
                            (workerId, self._heartbeatCounters.get(workerId, 0))
                        )
            for cellIndex, owners in candidates.items():
                claimed = self._claims.get(cellIndex)
                if claimed is not None and claimed[0] in aliveIds:
                    selectedOwner = claimed[0]
                else:
                    selectedOwner = max(owners, key=lambda owner: (owner[1], owner[0]))[0]
                teamIndex = next(
                    (
                        index + 1
                        for index, team in enumerate(teams)
                        if team["workerId"] == selectedOwner
                    ),
                    0,
                )
                board[cellIndex] = teamIndex
            for teamIndex in range(1, len(teams) + 1):
                ownedCells = {
                    cellIndex
                    for cellIndex, owner in enumerate(board)
                    if owner == teamIndex
                }
                components = connectedComponents(ownedCells)
                if len(components) > 1:
                    largestComponent = max(
                        components,
                        key=lambda component: (len(component), -min(component)),
                    )
                    for cellIndex in ownedCells - largestComponent:
                        board[cellIndex] = 0
            for teamIndex, team in enumerate(teams, start=1):
                team["territory"] = sum(owner == teamIndex for owner in board)
            return {
                "teams": teams,
                "board": board,
                "knownNodeCount": self._knownNodeCount,
                "error": self._error,
            }

    def _runThread(self) -> None:
        try:
            asyncio.run(self._runNetwork())
        except Exception as error:
            with self._lock:
                self._error = str(error)

    async def _runNetwork(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._stopAsyncEvent = asyncio.Event()
        if self._stopThreadEvent.is_set():
            self._stopAsyncEvent.set()
        runner = P4PRunner(netV4ListeningAddr=(self._host, 0))
        nodeGossiper = NodeGossiper(
            runner,
            syncIntervalSeconds=0.5,
            bootstrapNodes=self._bootstrapNodes,
        )
        gossipers:list[Gossiper] = []
        runnerStarted = False
        requestTask:asyncio.Task | None = None
        controlTask:asyncio.Task | None = None
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
                gossipTTLSeconds=12,
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
                gossipTTLSeconds=12,
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

            class ClaimListener:
                @EventListener
                async def onClaim(self, event:TerritoryClaimRecvedEvent) -> None:
                    try:
                        ownerId, sequence, cellIndex = decodeClaim(event.gossipContent)
                    except ValueError as error:
                        print(f"Ignored invalid territory claim: {error}")
                        return
                    with viewer._lock:
                        if not viewer._battleStarted:
                            return
                        current = viewer._claims.get(cellIndex, (b"", -1))
                        if (sequence, ownerId) > (current[1], current[0]):
                            viewer._claims[cellIndex] = (ownerId, sequence)
                        name, strength = createTeamProfile(ownerId)
                        viewer._teams.setdefault(ownerId, {
                            "name": name,
                            "strength": strength,
                            "active": False,
                        })
                    claimGossiper.addGossip(event.gossipContent, event.addr)

            class TeamListener:
                @EventListener
                async def onTeam(self, event:TerritoryTeamRecvedEvent) -> None:
                    try:
                        ownerId, counter, active = decodeTeam(event.gossipContent)
                    except ValueError as error:
                        print(f"Ignored invalid team announcement: {error}")
                        return
                    with viewer._lock:
                        if counter <= viewer._heartbeatCounters.get(ownerId, -1):
                            return
                        previous = viewer._latestHeartbeats.get(ownerId)
                        if previous is not None:
                            teamGossiper.deleteGossip(previous)
                        viewer._latestHeartbeats[ownerId] = event.gossipContent
                        viewer._heartbeatCounters[ownerId] = counter
                        name, strength = createTeamProfile(ownerId)
                        viewer._teams[ownerId] = {
                            "name": name,
                            "strength": strength,
                            "active": active,
                        }
                        viewer._lastSeen[ownerId] = time.monotonic()
                    teamGossiper.addGossip(event.gossipContent, event.addr)

            class SnapshotListener:
                @EventListener
                async def onSnapshot(
                    self,
                    event:TerritorySnapshotRecvedEvent,
                ) -> None:
                    try:
                        ownerId, counter, cells = decodeSnapshot(event.gossipContent)
                    except ValueError as error:
                        print(f"Ignored invalid territory snapshot: {error}")
                        return
                    with viewer._lock:
                        if not viewer._battleStarted:
                            return
                        previous = viewer._snapshots.get(ownerId)
                        if previous is None or counter > previous[0]:
                            viewer._snapshots[ownerId] = (counter, cells)
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
                    snapshotRequestGossiper.addGossip(
                        event.gossipContent,
                        event.addr,
                    )

            viewer = self
            runner.eventsManager.registerListener(ClaimListener())
            runner.eventsManager.registerListener(TeamListener())
            runner.eventsManager.registerListener(SnapshotListener())
            runner.eventsManager.registerListener(SnapshotRequestListener())
            for gossiper in gossipers:
                await gossiper.begin()

            async def requestTerritorySnapshots() -> None:
                counter = 0
                while not self._stopAsyncEvent.is_set():
                    counter = (counter + 1) & 0xFFFFFFFF
                    snapshotRequestGossiper.addGossip(
                        encodeSnapshotRequest(self._viewerId, counter)
                    )
                    await asyncio.sleep(3)

            async def sendBattleCommands() -> None:
                counter = 0
                while not self._stopAsyncEvent.is_set():
                    try:
                        command = self._commands.get_nowait()
                    except queue.Empty:
                        await asyncio.sleep(0.05)
                        continue
                    if command == BATTLE_COMMAND_RESET:
                        with self._lock:
                            self._claims.clear()
                            self._snapshots.clear()
                        for gossip in claimGossiper.gossips:
                            claimGossiper.deleteGossip(gossip)
                        for gossip in snapshotGossiper.gossips:
                            snapshotGossiper.deleteGossip(gossip)
                    counter = (counter + 1) & 0xFFFFFFFF
                    peers = {
                        node.addr
                        for node in nodeGossiper.nodeIdentifies
                    } | self._bootstrapNodes
                    if not peers:
                        with self._lock:
                            self._error = "No directly known P2P nodes to command."
                        continue
                    failedPeers = sendDirectBattleCommand(
                        runner.net,
                        peers,
                        self._viewerId,
                        time.time_ns() // 1_000_000,
                        counter,
                        command,
                    )
                    with self._lock:
                        self._error = (
                            "Direct command send failed for: "
                            + ", ".join(f"{host}:{port}" for host, port in failedPeers)
                            if failedPeers
                            else None
                        )

            requestTask = asyncio.create_task(requestTerritorySnapshots())
            controlTask = asyncio.create_task(sendBattleCommands())
            while not self._stopAsyncEvent.is_set():
                with self._lock:
                    self._knownNodeCount = len(nodeGossiper.nodeIdentifies)
                try:
                    await asyncio.wait_for(self._stopAsyncEvent.wait(), timeout=0.5)
                except TimeoutError:
                    pass
        finally:
            if requestTask is not None and not requestTask.done():
                requestTask.cancel()
                await asyncio.gather(requestTask, return_exceptions=True)
            if controlTask is not None and not controlTask.done():
                controlTask.cancel()
                await asyncio.gather(controlTask, return_exceptions=True)
            for gossiper in gossipers:
                await gossiper.end()
            if runnerStarted:
                await nodeGossiper.end()
                await runner.end()


class TerritoryWarDashboard:
    def __init__(self, root:tk.Tk, viewer:TerritoryViewer):
        self._root = root
        self._viewer = viewer
        self._cellItems:list[int] = []
        self._cellCanvasSize:tuple[int, int] | None = None
        self._cellFillColors:list[str | None] = []
        self._teams:list[dict] = []
        root.title("Territory Clash! | P2P Battle Observer")
        root.geometry("1000x760")
        root.minsize(760, 620)
        root.configure(bg=BACKGROUND)

        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure(
            "Battle.Horizontal.TProgressbar",
            troughcolor=PANEL,
            background="#70e1c1",
            bordercolor=PANEL,
            lightcolor="#70e1c1",
            darkcolor="#70e1c1",
        )

        tk.Label(
            root,
            text="TERRITORY CLASH!",
            font=("TkDefaultFont", 24, "bold"),
            fg="#70e1c1",
            bg=BACKGROUND,
        ).pack(anchor="w", padx=24, pady=(18, 0))
        tk.Label(
            root,
            text="A live map collected from the P2P teams. Start or reset the battle here.",
            font=("TkDefaultFont", 11),
            fg=MUTED,
            bg=BACKGROUND,
        ).pack(anchor="w", padx=27, pady=(0, 14))
        controls = tk.Frame(root, bg=BACKGROUND)
        controls.pack(fill="x", padx=24, pady=(0, 10))
        tk.Button(
            controls,
            text="Start",
            command=lambda: self._viewer.sendBattleCommand(BATTLE_COMMAND_START),
            bg="#70e1c1",
            fg="#101522",
            activebackground="#8bf0d2",
            relief="flat",
            padx=14,
            pady=7,
        ).pack(side="left", padx=(0, 8))
        tk.Button(
            controls,
            text="Reset",
            command=lambda: self._viewer.sendBattleCommand(BATTLE_COMMAND_RESET),
            bg="#e2a65b",
            fg="#101522",
            activebackground="#efb971",
            relief="flat",
            padx=14,
            pady=7,
        ).pack(side="left")

        self._canvas = tk.Canvas(
            root,
            bg=NEUTRAL,
            highlightthickness=1,
            highlightbackground="#2c374b",
        )
        self._canvas.pack(fill="both", expand=True, padx=24, pady=(0, 14))
        self._canvas.bind("<Configure>", self._drawBoard)
        teamFrame = tk.Frame(root, bg=BACKGROUND)
        teamFrame.pack(fill="x", padx=24, pady=(8, 4))
        self._teamsTable = ttk.Treeview(
            teamFrame,
            columns=("name", "strength", "territory", "state"),
            show="headings",
            height=8,
        )
        for column, title, width in (
            ("name", "Team", 150),
            ("strength", "Power", 70),
            ("territory", "Land", 70),
            ("state", "State", 90),
        ):
            self._teamsTable.heading(column, text=title)
            self._teamsTable.column(column, width=width, stretch=column == "name")
        teamScrollbar = ttk.Scrollbar(
            teamFrame,
            orient="vertical",
            command=self._teamsTable.yview,
        )
        self._teamsTable.configure(yscrollcommand=teamScrollbar.set)
        self._teamsTable.pack(side="left", fill="x", expand=True)
        teamScrollbar.pack(side="right", fill="y")
        self._statusLabel = tk.Label(
            root,
            text="Connecting to the bootstrap node...",
            font=("TkDefaultFont", 9),
            fg=MUTED,
            bg=BACKGROUND,
        )
        self._statusLabel.pack(anchor="w", padx=24, pady=(0, 12))
        self._root.protocol("WM_DELETE_WINDOW", self._close)
        self._refresh()

    def _refresh(self) -> None:
        data = self._viewer.snapshot()
        self._teams = data["teams"]
        if not self._cellItems:
            self._cellItems = [
                self._canvas.create_rectangle(
                    0,
                    0,
                    0,
                    0,
                    outline=BACKGROUND,
                    width=1,
                )
                for _ in range(BOARD_WIDTH * BOARD_HEIGHT)
            ]
            self._cellFillColors = [None] * len(self._cellItems)
        self._renderBoard(data["board"])
        orderedTeams = sorted(
            self._teams,
            key=lambda item: str(item["name"]).casefold(),
        )
        visibleIds = {team["id"] for team in orderedTeams}
        for itemId in self._teamsTable.get_children():
            if itemId not in visibleIds:
                self._teamsTable.delete(itemId)
        for team in orderedTeams:
            teamId = str(team["id"])
            tag = f"team-{teamId}"
            self._teamsTable.tag_configure(tag, foreground=str(team["color"]))
            values = (
                team["name"],
                team["strength"],
                team["territory"],
                (
                    "OFFLINE"
                    if not team["alive"]
                    else "PLAYING" if team["active"] else "WAITING"
                ),
            )
            if self._teamsTable.exists(teamId):
                self._teamsTable.item(teamId, values=values, tags=(tag,))
            else:
                self._teamsTable.insert(
                    "",
                    "end",
                    iid=teamId,
                    values=values,
                    tags=(tag,),
                )
        error = data["error"]
        self._statusLabel.configure(
            text=(
                f"P2P nodes known: {data['knownNodeCount']}  |  "
                f"Teams: {len(self._teams)}"
                + (f"  |  Network error: {error}" if error else "")
            )
        )
        self._root.after(120, self._refresh)

    def _drawBoard(self, _:tk.Event | None=None) -> None:
        self._renderBoard(self._viewer.snapshot()["board"])

    def _renderBoard(self, board:list[int]) -> None:
        if not self._cellItems:
            return
        width = max(1, self._canvas.winfo_width())
        height = max(1, self._canvas.winfo_height())
        cellWidth = width / BOARD_WIDTH
        cellHeight = height / BOARD_HEIGHT
        if self._cellCanvasSize != (width, height):
            for cellIndex, item in enumerate(self._cellItems):
                x = cellIndex % BOARD_WIDTH
                y = cellIndex // BOARD_WIDTH
                self._canvas.coords(
                    item,
                    x * cellWidth,
                    y * cellHeight,
                    (x + 1) * cellWidth,
                    (y + 1) * cellHeight,
                )
            self._cellCanvasSize = (width, height)
        colors = {
            index + 1: team["color"]
            for index, team in enumerate(self._teams)
        }
        for cellIndex, item in enumerate(self._cellItems):
            fill = colors.get(board[cellIndex], NEUTRAL)
            if self._cellFillColors[cellIndex] != fill:
                self._canvas.itemconfigure(item, fill=fill)
                self._cellFillColors[cellIndex] = fill

    def _close(self) -> None:
        self._viewer.stop()
        self._root.destroy()


def createParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Join a P2P territory battle and observe all teams."
    )
    parser.add_argument(
        "--bootstrap",
        action="append",
        type=parseBootstrapNode,
        required=True,
        metavar="HOST:PORT",
        help="Battle node to join; repeat for multiple bootstrap nodes",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Address to bind")
    return parser


def main(args:Sequence[str] | None=None) -> None:
    options = createParser().parse_args(args)
    viewer = TerritoryViewer(set(options.bootstrap), options.host)
    viewer.start()
    root = tk.Tk()
    TerritoryWarDashboard(root, viewer)
    root.mainloop()


if __name__ == "__main__":
    main()
