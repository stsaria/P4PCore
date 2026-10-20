import argparse
import ipaddress
import queue
import subprocess
import sys
import threading
import time
from collections.abc import Sequence
from pathlib import Path


EXAMPLES_DIR = Path(__file__).resolve().parent
NODE_SCRIPT = EXAMPLES_DIR / "autonomousSocialNode.py"
GUI_SCRIPT = EXAMPLES_DIR / "autonomousSocialGui.py"


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
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if not host or any(character.isspace() for character in host):
            raise argparse.ArgumentTypeError(
                "HOST must be a valid IP address or hostname"
            )
    return host, port


def createParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Launch autonomous P2P social agents and their monitoring GUI."
        )
    )
    parser.add_argument(
        "--nodes",
        type=int,
        default=8,
        help="Number of independent autonomous nodes to launch",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5,
        help="Seconds between posts on each node",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Address local demo processes bind to",
    )
    parser.add_argument(
        "--bootstrap",
        action="append",
        type=parseBootstrapNode,
        default=[],
        metavar="HOST:PORT",
        help="Existing remote peer; repeat for multiple peers",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Start agents without the monitoring GUI",
    )
    return parser


def buildLaunchCommands(
    nodeCount:int,
    intervalSeconds:float,
    host:str,
    bootstrapNodes:set[tuple[str, int]],
    launchGui:bool=True,
) -> tuple[list[list[str]], list[str] | None]:
    if nodeCount < 1:
        raise ValueError("nodeCount must be greater than 0")
    if intervalSeconds <= 0:
        raise ValueError("intervalSeconds must be greater than 0")
    peers = sorted(bootstrapNodes)
    nodeCommands = []
    for _ in range(nodeCount):
        command = [
            sys.executable,
            str(NODE_SCRIPT),
            "--host",
            host,
            "--interval",
            str(intervalSeconds),
            "--quiet",
        ]
        for peerHost, peerPort in peers:
            command.extend(["--bootstrap", f"{peerHost}:{peerPort}"])
        nodeCommands.append(command)
    guiCommand = None
    if launchGui:
        guiCommand = [sys.executable, str(GUI_SCRIPT), "--host", host]
        for peerHost, peerPort in peers:
            guiCommand.extend(["--bootstrap", f"{peerHost}:{peerPort}"])
    return nodeCommands, guiCommand


def _readProcessOutput(
    process:subprocess.Popen,
    readyPorts:queue.Queue[int],
) -> None:
    if process.stdout is None:
        return
    for line in process.stdout:
        print(line, end="", flush=True)
        if line.startswith("READY "):
            try:
                readyPorts.put(int(line.removeprefix("READY ").strip()))
            except ValueError:
                print(f"Ignoring invalid readiness message: {line.rstrip()}")


def _startProcess(
    command:list[str],
    readyPorts:queue.Queue[int],
) -> subprocess.Popen:
    process = subprocess.Popen(
        command,
        cwd=EXAMPLES_DIR.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    threading.Thread(
        target=_readProcessOutput,
        args=(process, readyPorts),
        daemon=True,
    ).start()
    return process


def _waitForReady(
    process:subprocess.Popen,
    readyPorts:queue.Queue[int],
) -> int:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("The first social node exited before becoming ready")
        try:
            return readyPorts.get(timeout=0.1)
        except queue.Empty:
            continue
    raise RuntimeError("Timed out waiting for the first social node to become ready")


def stopProcesses(processes:list[subprocess.Popen]) -> None:
    running = [process for process in processes if process.poll() is None]
    for process in running:
        process.terminate()
    deadline = time.monotonic() + 5
    for process in running:
        try:
            process.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def runParty(
    nodeCommands:list[list[str]],
    guiCommand:list[str] | None,
    host:str,
    bootstrapNodes:set[tuple[str, int]],
) -> int:
    processes:list[subprocess.Popen] = []
    readyPorts:queue.Queue[int] = queue.Queue()
    try:
        first = _startProcess(nodeCommands[0], readyPorts)
        processes.append(first)
        print("Started the first autonomous node.", flush=True)

        localBootstrap = None
        if not bootstrapNodes and (len(nodeCommands) > 1 or guiCommand is not None):
            port = _waitForReady(first, readyPorts)
            bootstrapHost = "127.0.0.1" if host in ("0.0.0.0", "::") else host
            localBootstrap = (bootstrapHost, port)

        for command in nodeCommands[1:]:
            if localBootstrap is not None:
                command.extend(
                    ["--bootstrap", f"{localBootstrap[0]}:{localBootstrap[1]}"]
                )
            process = _startProcess(command, readyPorts)
            processes.append(process)
            print("Started another autonomous node.", flush=True)

        guiProcess = None
        if guiCommand is not None:
            if localBootstrap is not None:
                guiCommand.extend(
                    ["--bootstrap", f"{localBootstrap[0]}:{localBootstrap[1]}"]
                )
            if not bootstrapNodes and localBootstrap is None:
                port = _waitForReady(first, readyPorts)
                bootstrapHost = "127.0.0.1" if host in ("0.0.0.0", "::") else host
                guiCommand.extend(["--bootstrap", f"{bootstrapHost}:{port}"])
            guiProcess = _startProcess(guiCommand, readyPorts)
            processes.append(guiProcess)
            print("Started the monitoring GUI.", flush=True)

        nodeProcesses = processes[:len(nodeCommands)]
        while True:
            if all(process.poll() is not None for process in nodeProcesses):
                return max(
                    (process.returncode or 0 for process in nodeProcesses),
                    default=0,
                )
            if guiProcess is not None and guiProcess.poll() is not None:
                print("Monitoring GUI closed; stopping local nodes.", flush=True)
                return guiProcess.returncode or 0
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("Stopping autonomous social network.", flush=True)
        return 130
    finally:
        stopProcesses(processes)


def main(args:Sequence[str] | None=None) -> int:
    options = createParser().parse_args(args)
    if options.nodes < 1:
        raise SystemExit("--nodes must be greater than 0")
    if options.interval <= 0:
        raise SystemExit("--interval must be greater than 0")
    try:
        nodeCommands, guiCommand = buildLaunchCommands(
            options.nodes,
            options.interval,
            options.host,
            set(options.bootstrap),
            not options.no_gui,
        )
    except ValueError as error:
        raise SystemExit(str(error)) from error
    return runParty(
        nodeCommands,
        guiCommand,
        options.host,
        set(options.bootstrap),
    )


if __name__ == "__main__":
    sys.exit(main())
