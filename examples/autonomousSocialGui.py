import argparse
import asyncio
import queue
import threading
import time
import tkinter as tk
from collections.abc import Sequence
from tkinter import ttk
if __package__:
    from examples.autonomousSocialCore import (
        MAX_FEED_POSTS,
        PeerStatus,
        SocialNode,
        SocialPost,
        createAgentName,
        createAgentRole,
        THEME_NAME,
    )
    from examples.autonomousSocialNode import parseBootstrapNode
else:
    from autonomousSocialCore import (
        MAX_FEED_POSTS,
        PeerStatus,
        SocialNode,
        SocialPost,
        createAgentName,
        createAgentRole,
        THEME_NAME,
    )
    from autonomousSocialNode import parseBootstrapNode
BACKGROUND = "#0d1117"
PANEL = "#161b22"
TEXT = "#e6edf3"
MUTED = "#8b949e"
ACCENT = "#58a6ff"
def getFeedInsertIndex(
    orderedKeys:list[tuple[int, bytes, int]],
    postKey:tuple[int, bytes, int],
) -> int:
    for index, existingKey in enumerate(orderedKeys):
        if postKey > existingKey:
            return index
    return len(orderedKeys)
class SocialMonitor:
    def __init__(
        self,
        host:str,
        bootstrapNodes:set[tuple[str, int]],
    ):
        self._host = host
        self._bootstrapNodes = bootstrapNodes
        self._events:queue.SimpleQueue[tuple[str, object]] = queue.SimpleQueue()
        self._stopThreadEvent = threading.Event()
        self._loopReadyEvent = threading.Event()
        self._loop:asyncio.AbstractEventLoop | None = None
        self._stopAsyncEvent:asyncio.Event | None = None
        self._thread = threading.Thread(target=self._runThread, daemon=True)
    def start(self) -> None:
        self._thread.start()
        if not self._loopReadyEvent.wait(timeout=3):
            raise RuntimeError("The social monitor event loop did not start")
    def stop(self) -> None:
        self._stopThreadEvent.set()
        self._loopReadyEvent.wait(timeout=1)
        if self._loop is not None and self._stopAsyncEvent is not None:
            self._loop.call_soon_threadsafe(self._stopAsyncEvent.set)
        if self._thread.is_alive():
            self._thread.join(timeout=4)
        if self._thread.is_alive():
            raise RuntimeError("The social monitor did not stop cleanly")
    def _runThread(self) -> None:
        try:
            asyncio.run(self._runAsync())
        except Exception as error:
            self._events.put(("error", str(error)))
    async def _runAsync(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._stopAsyncEvent = asyncio.Event()
        self._loopReadyEvent.set()
        socialNode = SocialNode(
            host=self._host,
            bootstrapNodes=self._bootstrapNodes,
            generatePosts=False,
            onPost=lambda post: self._events.put(("post", post)),
            onPeer=lambda peer: self._events.put(("peer", peer)),
            onError=lambda error: self._events.put(("error", error)),
        )
        try:
            port = await socialNode.start()
            self._events.put(("ready", port))
            await self._stopAsyncEvent.wait()
        finally:
            await socialNode.stop()
class AutonomousSocialDashboard:
    def __init__(self, root:tk.Tk, monitor:SocialMonitor):
        self._root = root
        self._monitor = monitor
        self._feedCards:list[
            tuple[tuple[int, bytes, int], tk.Frame, tk.Label]
        ] = []
        self._peers:dict[bytes, PeerStatus] = {}
        self._peerSignature = None
        self._postCount = 0
        self._error:str | None = None
        self._configureWindow()
        self._createWidgets()
        self._root.protocol("WM_DELETE_WINDOW", self._close)
        self._refresh()
    def _configureWindow(self) -> None:
        self._root.title(f"Tiny P2P Social — {THEME_NAME}")
        self._root.geometry("1120x780")
        self._root.minsize(820, 560)
        self._root.configure(bg=BACKGROUND)
        style = ttk.Style(self._root)
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=PANEL,
            foreground=TEXT,
            fieldbackground=PANEL,
            rowheight=30,
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background="#374151",
            foreground=TEXT,
            font=("TkDefaultFont", 10, "bold"),
        )
        style.map("Treeview", background=[("selected", "#1d4ed8")])
    def _createWidgets(self) -> None:
        header = tk.Frame(self._root, bg=BACKGROUND)
        header.pack(fill="x", padx=24, pady=(18, 14))
        tk.Label(header, text="P4PTesting", font=("TkDefaultFont", 22, "bold"),
                 fg=TEXT, bg=BACKGROUND).pack(side="left")
        self._countsLabel = tk.Label(header, text="Connecting…", font=("TkDefaultFont", 10),
                                      fg=MUTED, bg=BACKGROUND)
        self._countsLabel.pack(side="right", pady=8)
        shell = tk.Frame(self._root, bg=BACKGROUND)
        shell.pack(fill="both", expand=True, padx=24, pady=(0, 18))
        sidebar = tk.Frame(shell, bg=BACKGROUND, width=190)
        sidebar.pack(side="left", fill="y", padx=(0, 18))
        sidebar.pack_propagate(False)
        for label in ("⌂   Timeline",):
            tk.Label(sidebar, text=label, font=("TkDefaultFont", 12, "bold" if label.startswith("⌂") else "normal"),
                     fg=TEXT if label.startswith("⌂") else MUTED, bg=BACKGROUND,
                     anchor="w", padx=12, pady=12).pack(fill="x", pady=2)
        tk.Label(sidebar, text="YOUR NETWORK", font=("TkDefaultFont", 9, "bold"),
                 fg=MUTED, bg=BACKGROUND, anchor="w").pack(fill="x", padx=12, pady=(24, 8))
        self._peerList = tk.Frame(sidebar, bg=BACKGROUND)
        self._peerList.pack(fill="x")
        content = tk.Frame(shell, bg=BACKGROUND)
        content.pack(side="left", fill="both", expand=True)
        feedHeader = tk.Frame(content, bg=BACKGROUND)
        feedHeader.pack(fill="x", pady=(0, 12))
        tk.Label(feedHeader, text="Home", font=("TkDefaultFont", 18, "bold"),
                 fg=TEXT, bg=BACKGROUND).pack(side="left")
        self._feedCanvas = tk.Canvas(content, bg=BACKGROUND, highlightthickness=0, bd=0)
        self._feedInner = tk.Frame(self._feedCanvas, bg=BACKGROUND)
        self._feedWindow = self._feedCanvas.create_window((0, 0), window=self._feedInner, anchor="nw")
        self._feedInner.bind("<Configure>", lambda _: self._feedCanvas.configure(scrollregion=self._feedCanvas.bbox("all")))
        self._feedCanvas.bind("<Configure>", self._resizeFeedCards)
        self._feedCanvas.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(content, orient="vertical", command=self._feedCanvas.yview)
        self._feedCanvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
    def _refresh(self) -> None:
        while True:
            try:
                eventType, value = self._monitor._events.get_nowait()
            except queue.Empty:
                break
            if eventType == "post":
                post = value
                if isinstance(post, SocialPost):
                    self._addPost(post)
            elif eventType == "peer":
                peer = value
                if isinstance(peer, PeerStatus):
                    self._peers[peer.nodeId] = peer
            elif eventType == "error":
                self._error = str(value)
        self._refreshPeers()
        onlineCount = sum(peer.online for peer in self._peers.values())
        self._countsLabel.configure(
            text=(
f"{len(self._peers)} users  •  "
f"{self._postCount} posts received"
            )
        )
        if self._error:
            self._statusLabel.configure(
                text=f"Network error: {self._error}"
            )
        self._root.after(100, self._refresh)
    def _addPost(self, post:SocialPost) -> None:
        import hashlib
        self._postCount += 1
        createdAt = time.strftime("%b %d · %H:%M", time.localtime(post.createdAt / 1000))
        username = createAgentName(post.authorId)
        role = createAgentRole(post.authorId)
        card = tk.Frame(self._feedInner, bg=PANEL, padx=16, pady=14,
                        highlightthickness=1, highlightbackground="#30363d")
        postKey = (post.createdAt, post.authorId, post.sequence)
        orderedKeys = [entry[0] for entry in self._feedCards]
        insertIndex = getFeedInsertIndex(orderedKeys, postKey)
        before = self._feedCards[insertIndex][1] if insertIndex < len(self._feedCards) else None
        card.pack(fill="x", padx=0, pady=(0, 12), before=before)
        top = tk.Frame(card, bg=PANEL)
        top.pack(fill="x")
        avatar = tk.Canvas(top, width=42, height=42, bg=PANEL, highlightthickness=0)
        avatar.pack(side="left", padx=(0, 11))
        digest = hashlib.sha256(username.encode("utf-8")).digest()
        palette = ["#" + digest[i:i+3].hex() for i in (0, 3, 6)]
        avatar.create_oval(1, 1, 41, 41, fill=palette[0], outline="")
        cell = 6
        for y in range(5):
            for x in range(3):
                if digest[9 + y * 3 + x] & 1:
                    color = palette[(digest[24 + y + x] % len(palette))]
                    for xx in {x, 4-x}:
                        avatar.create_rectangle(6 + xx*cell, 6 + y*cell, 6 + (xx+1)*cell-1,
                                                6 + (y+1)*cell-1, fill=color, outline="")
        author = tk.Frame(top, bg=PANEL)
        author.pack(side="left", fill="x", expand=True, anchor="n")
        tk.Label(author, text=username, font=("TkDefaultFont", 11, "bold"),
                 fg=TEXT, bg=PANEL, anchor="w").pack(fill="x")
        tk.Label(author, text=f"{role}  ·  {createdAt}", font=("TkDefaultFont", 9),
                 fg=MUTED, bg=PANEL, anchor="w").pack(fill="x", pady=(2, 0))
        bodyLabel = tk.Label(card, text=post.text, font=("TkDefaultFont", 11), fg=TEXT,
                             bg=PANEL, anchor="w", justify="left",
                             wraplength=max(280, self._feedCanvas.winfo_width() - 100))
        bodyLabel.pack(fill="x", anchor="w", pady=(13, 12))
        actions = tk.Frame(card, bg=PANEL)
        actions.pack(fill="x")
        for symbol, label in (("♡", "Like"), ("◯", "Reply"), ("↗", "Share")):
            tk.Label(actions, text=f"{symbol}  {label}", font=("TkDefaultFont", 9),
                     fg=MUTED, bg=PANEL, padx=12).pack(side="left")
        self._feedCards.insert(insertIndex, (postKey, card, bodyLabel))
        if len(self._feedCards) > MAX_FEED_POSTS:
            _, oldCard, _ = self._feedCards.pop()
            oldCard.destroy()
    def _resizeFeedCards(self, event:tk.Event) -> None:
        self._feedCanvas.itemconfigure(self._feedWindow, width=event.width)
        wrapLength = max(240, event.width - 48)
        for _, _, bodyLabel in self._feedCards:
            bodyLabel.configure(wraplength=wrapLength)
    def _refreshPeers(self) -> None:
        import hashlib
        signature = tuple(sorted((nodeId, peer.online) for nodeId, peer in self._peers.items()))
        if signature == self._peerSignature:
            return
        self._peerSignature = signature
        for child in self._peerList.winfo_children():
            child.destroy()
        for nodeId, peer in sorted(self._peers.items(), key=lambda item: createAgentName(item[0]).lower()):
            name = createAgentName(nodeId)
            line = tk.Frame(self._peerList, bg=BACKGROUND)
            line.pack(fill="x", pady=5)
            avatar = tk.Canvas(line, width=28, height=28, bg=BACKGROUND, highlightthickness=0)
            avatar.pack(side="left", padx=(8, 8))
            digest = hashlib.sha256(name.encode("utf-8")).digest()
            color = "#" + digest[:3].hex()
            avatar.create_oval(1, 1, 27, 27, fill=color, outline="")
            for y in range(5):
                for x in range(3):
                    if digest[3 + y*3 + x] & 1:
                        for xx in {x, 4-x}:
                            avatar.create_rectangle(5+xx*3, 5+y*3, 7+xx*3, 7+y*3,
                                                    fill="#e6edf3", outline="")
            tk.Label(line, text=name, font=("TkDefaultFont", 9), fg=TEXT if peer.online else MUTED,
                     bg=BACKGROUND, anchor="w").pack(side="left", fill="x", expand=True)
            tk.Label(line, text="●", font=("TkDefaultFont", 8),
                     fg="#3fb950" if peer.online else "#6e7681", bg=BACKGROUND).pack(side="right", padx=5)
    def _close(self) -> None:
        self._monitor.stop()
        self._root.destroy()
def createParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Monitor autonomous posts on a P2P social network."
    )
    parser.add_argument("--host", default="0.0.0.0", help="Address to bind")
    parser.add_argument(
        "--bootstrap",
        action="append",
        type=parseBootstrapNode,
        default=[],
        metavar="HOST:PORT",
        help="Peer to join; repeat for multiple peers",
    )
    return parser
def main(args:Sequence[str] | None=None) -> None:
    options = createParser().parse_args(args)
    monitor = SocialMonitor(options.host, set(options.bootstrap))
    monitor.start()
    try:
        root = tk.Tk()
    except tk.TclError:
        monitor.stop()
        raise
    AutonomousSocialDashboard(root, monitor)
    root.mainloop()
if __name__ == "__main__":
    main()