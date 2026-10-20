import argparse
import asyncio
from collections.abc import Sequence

if __package__:
    from examples.autonomousSocialCore import (
        POST_INTERVAL_SECONDS,
        PeerStatus,
        SocialNode,
        SocialPost,
        createAgentName,
        createAgentRole,
    )
else:
    from autonomousSocialCore import (
        POST_INTERVAL_SECONDS,
        PeerStatus,
        SocialNode,
        SocialPost,
        createAgentName,
        createAgentRole,
    )


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


def createParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run an autonomous local social agent. NodeGossiper is used for "
            "peer discovery; posts are sent and relayed directly."
        )
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
    parser.add_argument(
        "--interval",
        type=float,
        default=POST_INTERVAL_SECONDS,
        help="Seconds between locally generated posts",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Keep agent logs in the dashboard instead of the terminal",
    )
    return parser


async def runNode(
    host:str,
    bootstrapNodes:set[tuple[str, int]],
    postIntervalSeconds:float,
    quiet:bool=False,
) -> None:
    socialNode = SocialNode(
        host=host,
        bootstrapNodes=bootstrapNodes,
        postIntervalSeconds=postIntervalSeconds,
        onPost=(
            None
            if quiet
            else lambda post: printPost(post, socialNode.nodeId)
        ),
        onPeer=None if quiet else printPeer,
    )
    try:
        port = await socialNode.start()
        print(f"READY {port}", flush=True)
        if not quiet:
            print(
                f"{createAgentName(socialNode.nodeId)} is generating local posts "
                f"every {postIntervalSeconds:g} seconds. Ctrl+C stops this node.",
                flush=True,
            )
        await asyncio.Event().wait()
    finally:
        await socialNode.stop()


def printPost(post:SocialPost, localId:bytes) -> None:
    label = (
        "You"
        if post.authorId == localId
        else f"{createAgentName(post.authorId)} · {createAgentRole(post.authorId)}"
    )
    print(f"[{label}] {post.text}", flush=True)


def printPeer(status:PeerStatus) -> None:
    state = "online" if status.online else "offline"
    print(f"Peer {status.nodeId.hex()[:8]} is {state}.", flush=True)


async def main(args:Sequence[str] | None=None) -> None:
    options = createParser().parse_args(args)
    if options.interval <= 0:
        raise SystemExit("--interval must be greater than 0")
    await runNode(
        options.host,
        set(options.bootstrap),
        options.interval,
        options.quiet,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
