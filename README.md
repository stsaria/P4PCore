# P4PCore
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/stsaria/P4PCore)
P4PCore is an asynchronous, P2P library built on the P4P protocol.
The P4P protocol is demonstrated in the programs within this repository.

## Getting Started
P4PCore is not published to PyPI or other pip repositories, so install it from a branch or release source.

pyproject.toml
```toml
[project]
dependencies = [
    "P4PCore==<version>"
]
```

bash
```
pip install git+https://github.com/stsaria/P4PCore.git@<version>
pip install .
```

This installs the library in the same way.

## Examples

`examples/territoryWar.py` runs exactly one team per process. Start one seed
node first, then launch each additional team as its own process. Stronger teams
expand faster. Each node advertises its team and territory over P2P gossip.
Nodes that lose their heartbeat are marked offline and their land becomes
available again after a short timeout:
Every team's territory is kept as one four-directionally connected region.
Expansion can only claim a neighboring cell, and a battle claim cannot cut an
opponent's territory into separate pieces.

To start a local battle with four independent nodes and the observer GUI in
one command:

```bash
python examples/territoryWarParty.py --nodes 4
```

The launcher assigns each team its own process and UDP port, then starts the
observer. Set `--nodes` to change the team count. Bootstrap peers can still be
provided and are forwarded to all teams and the observer:

```bash
python examples/territoryWarParty.py --nodes 8 --bootstrap 192.168.1.20:47474
```

To run just the teams without opening the GUI, add `--no-gui`. The observer
can also be started independently:

```bash
python examples/territoryWarParty.py --nodes 4 --no-gui
python examples/territoryWarGui.py --bootstrap 127.0.0.1:47474
```

The observer periodically asks the discovered nodes for their current territory
and also receives their regular updates, so it can join an ongoing battle.

For nodes on several computers, run one `territoryWar.py` process per
computer, as in the two-node example below. On each computer bind to
`--host 0.0.0.0`, set `--advertise-host` to that computer's reachable LAN IP,
and bootstrap joining nodes through the seed's LAN IP. Allow inbound UDP on
each team's listening port in the machine's firewall. There is no six-team
limit.

For an actual link-loss test, disconnect a team's LAN cable or disable its
network interface. Other reachable teams and the observer mark it offline
after the heartbeat timeout and remove its territory. The isolated process
may continue running locally, but it cannot publish or receive updates.
Use `--minutes` to change each team's default 30-minute run time.

```bash
python examples/territoryWar.py --host 0.0.0.0 --advertise-host 192.168.1.20 --port 47474 --name Red --strength 3
python examples/territoryWar.py --host 0.0.0.0 --advertise-host 192.168.1.21 --port 47474 --name Blue --strength 2 --bootstrap 192.168.1.20:47474
```

The Mandelbrot zoom demo is still available as `examples/piParty.py`, with its
separate viewer at `examples/piPartyGui.py`.
