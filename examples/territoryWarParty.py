import argparse
import ipaddress
import queue
import subprocess
import sys
import threading
import time
from collections.abc import Sequence
from pathlib import Path


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


EXAMPLES_DIR = Path(__file__).resolve().parent
TEAM_SCRIPT = EXAMPLES_DIR / "territoryWar.py"
VIEWER_SCRIPT = EXAMPLES_DIR / "territoryWarGui.py"


def createParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Launch independent territory nodes and the observer."
    )
    parser.add_argument("--nodes", type=int, default=4, help="Number of team processes")
    parser.add_argument("--host", default="127.0.0.1", help="Address each process binds to")
    parser.add_argument(
        "--bootstrap",
        action="append",
        type=parseBootstrapNode,
        default=[],
        metavar="HOST:PORT",
        help="Existing peer; repeat for multiple peers",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Start only the team processes",
    )
    return parser


def buildLaunchCommands(
    nodesCount:int,
    host:str,
    bootstrapNodes:set[tuple[str, int]],
    launchGui:bool=True,
) -> tuple[list[list[str]], list[str] | None]:
    if nodesCount < 1:
        raise ValueError("nodesCount must be greater than 0")
    peers = sorted(bootstrapNodes)
    teamCommands = []
    for _ in range(nodesCount):
        command = [sys.executable, str(TEAM_SCRIPT), "--host", host]
        for peerHost, peerPort in peers:
            command.extend(["--bootstrap", f"{peerHost}:{peerPort}"])
        teamCommands.append(command)

    guiCommand = None
    if launchGui:
        guiCommand = [sys.executable, str(VIEWER_SCRIPT), "--host", host]
        for peerHost, peerPort in peers:
            guiCommand.extend(["--bootstrap", f"{peerHost}:{peerPort}"])
    return teamCommands, guiCommand


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
                print(f"Ignoring invalid node readiness message: {line.rstrip()}")


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
            raise RuntimeError("The first territory node exited before becoming ready")
        try:
            return readyPorts.get(timeout=0.1)
        except queue.Empty:
            continue
    raise RuntimeError("Timed out waiting for the first territory node to become ready")


def stopProcesses(processes:list[subprocess.Popen]) -> None:
    running = [process for process in processes if process.poll() is None]
    for process in running:
        process.terminate()
    deadline = time.monotonic() + 5
    for process in running:
        timeout = max(0, deadline - time.monotonic())
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def runParty(
    teamCommands:list[list[str]],
    guiCommand:list[str] | None,
    host:str,
    bootstrapNodes:set[tuple[str, int]],
) -> int:
    processes:list[subprocess.Popen] = []
    readyPorts:queue.Queue[int] = queue.Queue()
    try:
        first = _startProcess(teamCommands[0], readyPorts)
        processes.append(first)
        print("Started the first territory node.", flush=True)

        localBootstrap = None
        if not bootstrapNodes and (len(teamCommands) > 1 or guiCommand is not None):
            port = _waitForReady(first, readyPorts)
            bootstrapHost = "127.0.0.1" if host in ("0.0.0.0", "::") else host
            localBootstrap = (bootstrapHost, port)

        for command in teamCommands[1:]:
            if localBootstrap is not None:
                command.extend(["--bootstrap", f"{localBootstrap[0]}:{localBootstrap[1]}"])
            process = _startProcess(command, readyPorts)
            processes.append(process)
            print("Started another territory node.", flush=True)

        guiProcess = None
        if guiCommand is not None:
            if localBootstrap is not None:
                guiCommand.extend([
                    "--bootstrap",
                    f"{localBootstrap[0]}:{localBootstrap[1]}",
                ])
            if not bootstrapNodes and localBootstrap is None:
                port = _waitForReady(first, readyPorts)
                bootstrapHost = "127.0.0.1" if host in ("0.0.0.0", "::") else host
                guiCommand.extend(["--bootstrap", f"{bootstrapHost}:{port}"])
            guiProcess = _startProcess(guiCommand, readyPorts)
            processes.append(guiProcess)
            print("Started territory observer GUI.", flush=True)

        while True:
            if all(process.poll() is not None for process in processes[:len(teamCommands)]):
                return max(
                    (process.returncode or 0 for process in processes[:len(teamCommands)]),
                    default=0,
                )
            if guiProcess is not None and guiProcess.poll() is not None:
                print("Observer GUI closed; stopping territory nodes.", flush=True)
                return guiProcess.returncode or 0
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("Stopping territory battle.", flush=True)
        return 130
    finally:
        stopProcesses(processes)


def main(args:Sequence[str] | None=None) -> int:
    options = createParser().parse_args(args)
    if options.nodes < 1:
        raise SystemExit("--nodes must be greater than 0")
    try:
        teamCommands, guiCommand = buildLaunchCommands(
            options.nodes,
            options.host,
            set(options.bootstrap),
            not options.no_gui,
        )
    except ValueError as error:
        raise SystemExit(str(error)) from error
    return runParty(
        teamCommands,
        guiCommand,
        options.host,
        set(options.bootstrap),
    )


if __name__ == "__main__":
    sys.exit(main())
