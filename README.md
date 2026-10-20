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

`examples/territoryWar.py` runs exactly one team per process. Every node joins
the P2P network and waits for the observer GUI to start or pause the battle.
Team names and strengths are generated automatically, and each node binds to an
OS-assigned UDP port. NodeGossiper shares reachable node addresses; the team
protocol carries no manually configured addresses. Nodes that lose their
heartbeat are marked offline, but their territory remains on the board; other
teams can take those cells only by invading them.
At battle start, each team chooses a random empty cell farthest from the
territory it currently knows about, helping teams begin well apart.
Every team's territory is kept as one four-directionally connected region.
Expansion can only claim a neighboring cell, and a battle claim cannot cut an
opponent's territory into separate pieces. A team expands from a cell when at
least three of its eight surrounding directions are not its own territory;
enemy territory can only be invaded when it has at least three such
dissatisfied directions and the invasion preserves the opponent's connectivity.
Expansion now claims more cells at shorter intervals, with claim gossip sent
more frequently so the faster pace reaches the other nodes. Territory
snapshots are divided into network-sized chunks. The board is 192 by 126
cells, 2.25 times the previous grid resolution, while the GUI still updates
the display continuously.

The lower node ID starts each match. Moves are acknowledged and retried in case
a UDP packet is lost. Press Ctrl+C to exit.

For an autonomous, multi-node social feed, run:

```bash
python examples/autonomousSocialParty.py --nodes 8
```

The dashboard shows each agent's posts and whether its node is online. Each
node participates in one shared story: turning an empty shop in a port town
into a neighborhood cafe. Agents have different roles, make concrete
suggestions, share progress and concerns, and sometimes respond to a recent
post from another agent. The feed shows the full text and each agent's role.
Posts are created locally every five seconds by default. Eight nodes therefore
produce about 96 posts per minute. Set `--interval 1` for about 480 posts per
minute.

The Japanese dialogue is generated locally from theme-specific writing
patterns and recent posts; it does not call an AI service, need an API key, or
consume a provider's free tier, so generation has no external usage fee. It is
not an LLM, but unlike the previous unrelated phrase combinations, each
agent's post is about the shared cafe project and can refer to another agent's
idea.

NodeGossiper is used only to discover peers. Posts and heartbeats use a
separate direct P2P protocol and are relayed by nodes, not added to Gossip.
There is no central server. Posts are acknowledged by the next-hop peer and
retried until acknowledged, so a lost UDP packet does not silently disappear.
If the initial/bootstrap machine disconnects after the other nodes have
discovered one another, the remaining connected nodes continue generating,
receiving, and relaying posts without it. A new node cannot discover the
network through a stopped bootstrap address, so configure more than one
reachable bootstrap peer when you need to join during a failure. The dashboard
marks a peer offline after six seconds without a heartbeat.

To run on several computers, start one node on the first computer and note its
`READY` port. Start additional nodes and the dashboard with one or more reachable peer
addresses. Repeat `--bootstrap HOST:PORT` to configure redundant entry points.
Allow inbound UDP traffic on the selected port and each node's
assigned UDP port in the host firewalls:

```bash
# First computer
python examples/autonomousSocialNode.py --host 0.0.0.0

# Other computers
python examples/autonomousSocialNode.py --host 0.0.0.0 --bootstrap 192.168.1.20:PORT_FROM_READY
python examples/autonomousSocialGui.py --host 0.0.0.0 --bootstrap 192.168.1.20:PORT_FROM_READY
# Optional additional reachable entry point
python examples/autonomousSocialNode.py --host 0.0.0.0 --bootstrap 192.168.1.20:PORT_FROM_READY --bootstrap 192.168.1.21:ANOTHER_PORT
```

The local party launcher also accepts `--interval` and `--no-gui`. A node can
be stopped independently with Ctrl+C; the remaining nodes continue operating.

To start a local battle with four independent nodes and the observer GUI in
one command:

```bash
python examples/territoryWarParty.py --nodes 4
```

The launcher starts each team in its own process, lets the first node choose
its UDP port, and bootstraps the other local processes and observer through it.
Use **Start** and **Reset** in the GUI to control the game. Each command is
sent directly to every node currently known to the GUI, without forwarding it
through Gossip. Reset clears the board and stops expansion. Set `--nodes` to
change the team count.
When joining an existing network, pass one or more bootstrap peers:

```bash
python examples/territoryWarParty.py --nodes 8 --bootstrap 192.168.1.20:PORT_FROM_READY
```

To run just the waiting team nodes without opening the GUI, add `--no-gui`.
The observer can also be started independently:

```bash
python examples/territoryWarParty.py --nodes 4 --no-gui
python examples/territoryWarGui.py --bootstrap 192.168.1.20:PORT_FROM_READY
```

The observer periodically asks the discovered nodes for their current territory
and also receives their regular updates, so it can join an ongoing battle.

For nodes on several computers, run one `territoryWar.py` process per
computer. The first node can be started without a bootstrap peer; it prints
its assigned UDP port as `READY <port>`. Start each additional node with the
first node's LAN address and printed port. Allow inbound UDP traffic on the
selected port at the seed node and on each node's assigned UDP port in the
machine firewalls; assigned ports may change when a node restarts, so firewall
rules must allow the resulting dynamic UDP ports. No team count is built in.

```bash
# Seed CT: note the port printed in its READY line.
python examples/territoryWar.py

# Other CTs and the GUI: use the seed CT's IP and printed port.
python examples/territoryWar.py --bootstrap 192.168.1.20:PORT_FROM_READY
python examples/territoryWarGui.py --bootstrap 192.168.1.20:PORT_FROM_READY
```

For an actual link-loss test, disconnect a team's LAN cable or disable its
network interface. Other reachable teams and the observer mark it offline
after the heartbeat timeout and remove its territory. The isolated process
may continue running locally, but it cannot publish or receive updates.
The Mandelbrot zoom demo is still available as `examples/piParty.py`, with its
separate viewer at `examples/piPartyGui.py`.
