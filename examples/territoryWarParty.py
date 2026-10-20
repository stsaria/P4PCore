import argparse
import ipaddress
import subprocess
import sys
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
        description="Launch several independent territory teams and the observer."
    )
    parser.add_argument("--nodes", type=int, default=4, help="Number of team processes")
    parser.add_argument("--host", default="127.0.0.1", help="Address each team binds to")
    parser.add_argument(
        "--advertise-host",
        help="LAN-reachable IP announced by teams when binding to 0.0.0.0",
    )
    parser.add_argument("--port", type=int, default=12598, help="First team UDP port")
    parser.add_argument(
        "--minutes",
        type=float,
        default=30,
        help="Run time for each team (default: 30 minutes)",
    )
    parser.add_argument(
        "--name-prefix",
        default="Team",
        help="Prefix for generated team names (default: Team)",
    )
    parser.add_argument(
        "--strength",
        type=int,
        default=1,
        help="First team's strength; subsequent teams gain one strength each",
    )
    parser.add_argument(
        "--bootstrap",
        action="append",
        type=parseBootstrapNode,
        default=[],
        metavar="HOST:PORT",
        help="Existing peer for teams and observer; repeat for multiple peers",
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
    port:int,
    minutes:float,
    namePrefix:str,
    firstStrength:int,
    bootstrapNodes:set[tuple[str, int]],
    advertiseHost:str | None,
    launchGui:bool=True,
) -> tuple[list[list[str]], list[str] | None]:
    if nodesCount < 1:
        raise ValueError("nodesCount must be greater than 0")
    highestPort = port + nodesCount if launchGui else port + nodesCount - 1
    if not 1 <= port <= 65535 or highestPort > 65535:
        raise ValueError("team and observer port range must fit between 1 and 65535")
    if firstStrength < 1 or firstStrength + nodesCount - 1 > 255:
        raise ValueError("strength range must fit between 1 and 255")
    if minutes <= 0:
        raise ValueError("minutes must be greater than 0")
    if not namePrefix:
        raise ValueError("namePrefix must not be empty")

    seed = next(iter(sorted(bootstrapNodes)), None)
    localSeed = (host if host not in ("0.0.0.0", "::") else advertiseHost, port)
    if seed is None:
        if localSeed[0] is None:
            raise ValueError("advertiseHost is required when host is a wildcard")
        seed = (str(localSeed[0]), port)

    teamCommands = []
    for index in range(nodesCount):
        name = f"{namePrefix}{index + 1}"
        if len(name.encode("utf-8")) > 16:
            raise ValueError("generated team names must fit within 16 UTF-8 bytes")
        teamPort = port + index
        command = [
            sys.executable,
            str(TEAM_SCRIPT),
            "--host",
            host,
            "--port",
            str(teamPort),
            "--name",
            name,
            "--strength",
            str(firstStrength + index),
            "--minutes",
            str(minutes),
        ]
        if advertiseHost:
            command.extend(["--advertise-host", advertiseHost])
        peers = set(bootstrapNodes)
        if index > 0 and not peers:
            peers.add((str(seed[0]), port))
        for peerHost, peerPort in sorted(peers):
            command.extend(["--bootstrap", f"{peerHost}:{peerPort}"])
        teamCommands.append(command)

    guiCommand = None
    if launchGui:
        guiCommand = [
            sys.executable,
            str(VIEWER_SCRIPT),
            "--host",
            host,
            "--port",
            str(port + nodesCount),
        ]
        for peerHost, peerPort in sorted(set(bootstrapNodes) or {seed}):
            guiCommand.extend(["--bootstrap", f"{peerHost}:{peerPort}"])
    return teamCommands, guiCommand


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
) -> int:
    processes:list[subprocess.Popen] = []
    try:
        for command in teamCommands:
            process = subprocess.Popen(command, cwd=EXAMPLES_DIR.parent)
            processes.append(process)
            print(f"Started team process: {' '.join(command[-6:])}", flush=True)
            time.sleep(0.25)

        guiProcess = None
        if guiCommand is not None:
            guiProcess = subprocess.Popen(guiCommand)
            processes.append(guiProcess)
            print("Started territory observer GUI.", flush=True)

        while True:
            teamProcesses = processes[:len(teamCommands)]
            if all(process.poll() is not None for process in teamProcesses):
                return max((process.returncode or 0 for process in teamProcesses), default=0)
            if guiProcess is not None and guiProcess.poll() is not None:
                print("Observer GUI closed; stopping team processes.", flush=True)
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
    if not 1 <= options.port <= 65535:
        raise SystemExit("--port must be between 1 and 65535")
    lastPortOffset = options.nodes if not options.no_gui else options.nodes - 1
    if options.port + lastPortOffset > 65535:
        raise SystemExit("team and observer ports must fit between 1 and 65535")
    if options.minutes <= 0:
        raise SystemExit("--minutes must be greater than 0")
    if options.strength < 1 or options.strength + options.nodes - 1 > 255:
        raise SystemExit("team strengths must fit between 1 and 255")
    if options.host in ("0.0.0.0", "::") and not options.advertise_host:
        raise SystemExit("--advertise-host is required when --host is a wildcard")
    try:
        teamCommands, guiCommand = buildLaunchCommands(
            options.nodes,
            options.host,
            options.port,
            options.minutes,
            options.name_prefix,
            options.strength,
            set(options.bootstrap),
            options.advertise_host,
            not options.no_gui,
        )
    except ValueError as error:
        raise SystemExit(str(error)) from error
    if guiCommand is not None and options.host in ("0.0.0.0", "::"):
        guiCommand[guiCommand.index("--host") + 1] = "127.0.0.1"
    return runParty(teamCommands, guiCommand)


if __name__ == "__main__":
    sys.exit(main())
