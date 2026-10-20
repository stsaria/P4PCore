from __future__ import annotations

import asyncio
import random
import struct
import time
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from P4PCore.P4PRunner import P4PRunner
from P4PCore.core.abstract.NetHandler import NetHandler
from P4PCore.core.protocol.Protocol import PacketElementSize, PacketFlag
from P4PCore.common.util.BytesCoverter import itob
from P4PCore.plugin.append.nodeGossiper.NodeGossiper import NodeGossiper


SOCIAL_UUID = UUID("cd8ea9ca-3a9c-4d3b-af9c-46d9f0172d09")
HEARTBEAT = 1
POST = 2
POST_ACK = 3
HEARTBEAT_FORMAT = "!B32sI"
POST_FORMAT = "!B32s32sIQH"
POST_ACK_FORMAT = "!B32s32sI"
HEARTBEAT_SIZE = 37
POST_HEADER_SIZE = 79
POST_ACK_SIZE = 69
MAX_POST_BYTES = 900
MAX_KNOWN_POSTS = 5000
MAX_RECENT_POSTS = 1000
MAX_POSTS_PER_PEER_SYNC = 50
MAX_PENDING_POSTS_PER_PEER = 250
POST_RETRY_INTERVAL_SECONDS = 2
MAX_POST_RETRIES_PER_PEER_SYNC = 10
PEER_TIMEOUT_SECONDS = 6
HEARTBEAT_INTERVAL_SECONDS = 1
POST_INTERVAL_SECONDS = 5
MAX_FEED_POSTS = 500

THEME_NAME = "メイドカフェを立てる"
THEME_DESCRIPTION = (
    "港の朝市で食材を仕入れ、古い空き店舗を改装して、 "
    "近所の人が気軽に立ち寄れる喫茶店を開く計画"
)
AGENT_NAMES = (
    "Mugi",
    "Sora",
    "Kumo",
    "Hana",
    "Nagi",
    "Yuzu",
    "Rin",
    "Momo",
    "Aoi",
    "Tsumugi",
    "Kohaku",
    "Sumi",
)
AGENT_ROLES = (
    "メニューを考える人",
    "内装を直す人",
    "港の人と話す人",
    "お金の計算をする人",
    "店の広報をする人",
    "コーヒーを淹れる人",
    "近所の子どもを見守る人",
    "店全体をまとめる人",
)
MENU_IDEAS = (
    "朝市のレモンで作る、甘さ控えめのソーダ",
    "売れ残ったパンを使った、焼きたてのフレンチトースト",
    "港の果物屋さんの柑橘を使った季節のタルト",
    "漁から戻った人でも食べやすい、具だくさんのスープ",
    "深煎りの豆と近くの牧場のミルクで作るカフェオレ",
    "店先で育てたミントを使う、食後のハーブティー",
    "朝の忙しい人向けの、小さな持ち帰りおにぎり",
    "形が不ぞろいな果物も使う、日替わりのジャムトースト",
    "雨の日だけ出す、シナモン入りのホットミルク",
    "子どもと分けやすい、小さめの焼き菓子セット",
    "常連さんが飽きないように週替わりにする豆",
    "魚市場の人が休憩中につまめる、塩味のスコーン",
)
SHOP_IDEAS = (
    "窓際に二人掛けの席を置いて、港が見えるようにする",
    "古いカウンターは磨いて残し、傷も店の歴史として見せる",
    "入口に黒板を置いて、その日のおすすめを手書きする",
    "棚の一角を近所の人の本棚にして、読み終えた本を交換する",
    "雨の日に濡れた傘を置ける場所を、入口の横に作る",
    "朝市帰りの人が荷物を置けるよう、椅子の間を広めにする",
    "壁の塗装はみんなでやって、少しずつ色を重ねる",
    "使える古道具は捨てずに直して、店の備品にする",
    "一人でも気まずくないよう、カウンター席を多めにする",
    "閉店後に近所の人が集まれる、小さな読書会を開く",
    "子どもが待てるよう、絵本と色鉛筆を置いておく",
    "店の名前は、港から見える灯台にちなんだものにする",
)
CONCERNS = (
    "最初から品数を増やすと仕込みが回らないので、まずは三つに絞りたいです。",
    "見積もりを取ったら床の修理が思ったより高くて、どこを自分たちで直すか相談したいです。",
    "朝市の仕入れは楽しみだけど、売れ残りを出さない量を一緒に考えたいです。",
    "港が見える席は魅力的だけど、冬のすきま風は先に何とかしたいですね。",
    "誰でも来やすい場所にしたいので、値段は背伸びしすぎない方がいいと思います。",
    "開店日を急ぐより、近所の人に試食してもらう日を先に作りませんか。",
    "古い設備を全部残すのは難しそう。安全に使えるものを選んで直したいです。",
    "宣伝より先に、朝市の人たちに計画を話してみるのがよさそうです。",
    "忙しい日でも一人で回せるよう、注文の流れを簡単にしておきたいです。",
    "雨漏りの場所がまだ分からないので、次の雨の日に一度見に来ませんか。",
)
PROGRESS_NOTES = (
    "今日は朝市でレモンを分けてもらえました。来週、ソーダの試作を持っていきます。",
    "カウンターを磨いてみたら、木目が思ったよりきれいに出ました。これは残したいな。",
    "近所の方に声をかけたら、昔この店でコーヒーを飲んでいた話を聞けました。",
    "壁の色を試し塗りしました。白より少し温かい色の方が、夕方の光に合いそうです。",
    "試作のスープ、魚市場の方に味見してもらいました。塩気を少し控えることにします。",
    "古い棚を直せる人が見つかりました。捨てずに済みそうで、ほっとしています。",
    "黒板の文字を練習中です。まっすぐ書くのって、意外と難しいですね。",
    "今日は窓を開けて片付けました。潮の匂いが入ってきて、この場所らしいなと思いました。",
    "椅子を二脚だけ置いてみました。通路が狭くならないか、もう一度測ってみます。",
    "朝市の帰りに寄ってくれる人が何人かいました。開店前なのに、もう少し店らしくなってきた。",
    "近所の子が店名の候補を考えてくれました。大人にはない発想で面白かったです。",
    "仕入れ先と相談して、形のそろわない果物も使わせてもらえることになりました。",
)
REFLECTIONS = (
    "やっぱり、店は内装だけじゃなくて、来る人とのやりとりでできていくんですね。",
    "最初は自分たちだけで決めるつもりだったけど、近所の人に聞く方がずっと早かった。",
    "急いで完成させるより、少しずつ手を入れていく方がこの建物には合っている気がします。",
    "ちゃんと続けるには、理想だけじゃなくて毎日の仕込みの量も考えないとですね。",
    "誰かがふらっと入って、何も話さなくても休める場所にしたいです。",
    "この計画を話すと、みんな自分の思い出を聞かせてくれるのが嬉しいです。",
    "派手な店じゃなくても、帰り道に思い出してもらえる店なら十分かもしれません。",
    "一人で考えていた時より、みんなの得意なことが見えてきました。",
    "店を開ける日が近づくほど、ちゃんと迎えられるか少し緊張してきました。",
    "今日決めたことを一つずつ形にすれば、きっと大丈夫だと思いたいです。",
)
POST_REFERENCES = (
    ("レモン", "レモンのソーダ"),
    ("ソーダ", "ソーダの案"),
    ("フレンチトースト", "フレンチトースト"),
    ("タルト", "季節のタルト"),
    ("スープ", "スープ"),
    ("カフェオレ", "カフェオレ"),
    ("ハーブティー", "ハーブティー"),
    ("おにぎり", "持ち帰りのおにぎり"),
    ("ジャムトースト", "ジャムトースト"),
    ("スコーン", "スコーン"),
    ("カウンター", "カウンター"),
    ("窓際", "窓際の席"),
    ("黒板", "黒板のおすすめ"),
    ("本棚", "本棚の案"),
    ("傘", "傘置き場"),
    ("朝市", "朝市での仕入れ"),
    ("塗装", "壁の色"),
    ("古道具", "古道具の修理"),
    ("一人", "一人でも過ごせる席"),
    ("子ども", "子ども向けの工夫"),
    ("読書会", "読書会"),
    ("灯台", "灯台にちなんだ店名"),
    ("雨漏り", "雨漏りの修理"),
    ("仕込み", "仕込みの量"),
    ("近所", "近所の人への相談"),
    ("開店", "開店日のこと"),
    ("試作", "試作品"),
    ("店名", "店の名前"),
)
ROLE_FOLLOWUPS = {
    "メニューを考える人": "味の組み合わせを考えて、次の試作に持っていきます。",
    "内装を直す人": "次の作業日に寸法を測って、できるところから手を入れます。",
    "港の人と話す人": "今度の朝市で、近所の方にも感想を聞いてみます。",
    "お金の計算をする人": "材料費と手間を一度計算して、無理のない形を考えます。",
    "店の広報をする人": "お知らせに載せる時も、その良さが伝わる言葉を考えます。",
    "コーヒーを淹れる人": "豆の量を変えて何通りか淹れ、みんなで味を見たいです。",
    "近所の子どもを見守る人": "子ども連れでも過ごしやすいか、家族にも聞いてみます。",
    "店全体をまとめる人": "やることを小分けにして、次の作業日に相談しましょう。",
}


@dataclass(frozen=True)
class SocialPost:
    authorId:bytes
    sequence:int
    createdAt:int
    text:str

    @property
    def key(self) -> tuple[bytes, int]:
        return self.authorId, self.sequence


@dataclass(frozen=True)
class PeerStatus:
    nodeId:bytes
    address:tuple[str, int]
    online:bool
    lastSeen:float | None


def createAgentName(nodeId:bytes) -> str:
    if len(nodeId) != 32:
        raise ValueError("nodeId must be 32 bytes")
    index = int.from_bytes(nodeId[4:8], "big") % len(AGENT_NAMES)
    return f"{AGENT_NAMES[index]}-{nodeId[:4].hex()}"


def createAgentRole(nodeId:bytes) -> str:
    if len(nodeId) != 32:
        raise ValueError("nodeId must be 32 bytes")
    index = int.from_bytes(nodeId[8:12], "big") % len(AGENT_ROLES)
    return AGENT_ROLES[index]


def getPostReference(text:str) -> str:
    for keyword, reference in POST_REFERENCES:
        if keyword in text:
            return reference
    excerpt = text.split("。", 1)[0].rstrip("、，, ")
    if len(excerpt) > 24:
        excerpt = excerpt[:23].rstrip() + "…"
    return excerpt


def generatePost(
    nodeId:bytes,
    sequence:int,
    seed:int | None=None,
    recentPosts:list[SocialPost] | None=None,
) -> SocialPost:
    if len(nodeId) != 32:
        raise ValueError("nodeId must be 32 bytes")
    if not 0 <= sequence <= 0xFFFFFFFF:
        raise ValueError("post sequence must fit in 4 bytes")
    generator = random.Random(seed)
    role = createAgentRole(nodeId)
    peerPosts = [
        post for post in (recentPosts or [])
        if post.authorId != nodeId
    ]
    if peerPosts and generator.random() < 0.58:
        post = generator.choice(peerPosts)
        author = createAgentName(post.authorId)
        reference = getPostReference(post.text)
        replies = (
            "いいですね。まずは少量で試して、朝市の人にも感想を聞いてみたいです。",
            "なるほど。実際にやるなら、何から始めるのがよさそうですか？",
            "面白い案ですね。費用と準備にかかる時間を、一度確かめてみませんか。",
            "それなら、開店前に近所の人にも試してもらえると安心ですね。",
            "私も賛成です。無理なく続けられる形にできたらいいな。",
            "いいと思います。ほかの案とも比べて、次の集まりで決めましょう。",
            "たしかに、その方がこの店らしくなりそう。私にも手伝わせてください。",
            "少し気になる点もあります。忙しい朝でも同じようにできそうでしょうか？",
            "そういう考え方は好きです。できるところから一緒に試してみましょう。",
            "いいですね。使う人のことを考えているのが伝わってきます。",
            "なるほど、見落としていました。もう少し詳しく聞いてもいいですか？",
            "その方向で進めたいです。まずは小さく始めて、様子を見ましょう。",
        )
        text = (
            f"{author}さんの{reference}の案、{generator.choice(replies)}"
            f"{ROLE_FOLLOWUPS[role]}"
        )
    else:
        if sequence <= 3:
            text = generator.choice((
                f"この店で最初に出すメニュー、{generator.choice(MENU_IDEAS)}はどうでしょう。港の朝市で材料をそろえられそうです。",
                f"空き店舗を見てきました。窓際から港が見えるので、{generator.choice(SHOP_IDEAS)}のがよさそうです。",
                f"まず近所の人に計画を聞いてみたいです。{generator.choice(CONCERNS)}",
                f"{role}として、最初に決めたいのは毎日無理なく続けられる形です。{generator.choice(SHOP_IDEAS)}のはどうかな。",
            ))
        elif sequence < 21:
            text = generator.choice((
                generator.choice(PROGRESS_NOTES),
                f"次の作業日、{generator.choice(SHOP_IDEAS)}を試してみます。来られる人がいたら一緒にやりましょう。",
                f"メニューを考えていて、{generator.choice(MENU_IDEAS)}を試作したいと思いました。味見してくれる人を募集中です。",
                f"{generator.choice(CONCERNS)} まずはできるところから進めましょう。",
            ))
        elif sequence < 121:
            text = generator.choice((
                f"試作してみました。{generator.choice(MENU_IDEAS)}は、もう少し甘さを控えた方が朝でも食べやすそうです。",
                f"開店前に近所の方を招いて、短いお試し営業をしたいです。{generator.choice(SHOP_IDEAS)}もその時に感想を聞けそう。",
                f"準備が進んできました。{generator.choice(PROGRESS_NOTES)}",
                f"開店日のことを考えると少し緊張します。{generator.choice(CONCERNS)}",
            ))
        else:
            text = generator.choice((
                generator.choice(REFLECTIONS),
                f"今日も店を開けられました。{generator.choice(PROGRESS_NOTES)}来てくれた皆さん、ありがとう。",
                f"最近よく出るのは、{generator.choice(MENU_IDEAS)}です。次は季節の食材でも試してみたいな。",
                f"これからも、{generator.choice(SHOP_IDEAS)}という雰囲気を大事にしていきたいです。",
            ))
        if peerPosts and generator.random() < 0.28:
            post = generator.choice(peerPosts)
            author = createAgentName(post.authorId)
            quote = post.text[:24]
            text = (
                f"{author}さんの「{quote}」という話、覚えています。"
                f"{text}"
            )
    return SocialPost(
        nodeId,
        sequence,
        int(time.time() * 1000),
        text,
    )


def encodeHeartbeat(nodeId:bytes, sequence:int) -> bytes:
    if len(nodeId) != 32:
        raise ValueError("nodeId must be 32 bytes")
    if not 0 <= sequence <= 0xFFFFFFFF:
        raise ValueError("heartbeat sequence must fit in 4 bytes")
    return struct.pack(HEARTBEAT_FORMAT, HEARTBEAT, nodeId, sequence)


def encodePostAcknowledgement(
    nodeId:bytes,
    authorId:bytes,
    sequence:int,
) -> bytes:
    if len(nodeId) != 32 or len(authorId) != 32:
        raise ValueError("node IDs must be 32 bytes")
    if not 0 <= sequence <= 0xFFFFFFFF:
        raise ValueError("post sequence must fit in 4 bytes")
    return struct.pack(
        POST_ACK_FORMAT,
        POST_ACK,
        nodeId,
        authorId,
        sequence,
    )


def encodePostPacket(senderId:bytes, post:SocialPost) -> bytes:
    if len(senderId) != 32 or len(post.authorId) != 32:
        raise ValueError("node IDs must be 32 bytes")
    if not 0 <= post.sequence <= 0xFFFFFFFF:
        raise ValueError("post sequence must fit in 4 bytes")
    if not 0 <= post.createdAt <= 0xFFFFFFFFFFFFFFFF:
        raise ValueError("post timestamp must fit in 8 bytes")
    text = post.text.encode("utf-8")
    if not text or len(text) > MAX_POST_BYTES:
        raise ValueError(f"post must contain 1 to {MAX_POST_BYTES} UTF-8 bytes")
    if b"\0" in text:
        raise ValueError("post cannot contain a null character")
    return struct.pack(
        POST_FORMAT,
        POST,
        senderId,
        post.authorId,
        post.sequence,
        post.createdAt,
        len(text),
    ) + text


def decodeSocialPacket(
    data:bytes,
) -> tuple[int, bytes, int, SocialPost | None, bytes | None]:
    if len(data) == HEARTBEAT_SIZE:
        packetType, nodeId, sequence = struct.unpack(HEARTBEAT_FORMAT, data)
        if packetType != HEARTBEAT:
            raise ValueError("unknown social packet type")
        return HEARTBEAT, nodeId, sequence, None, None

    if len(data) == POST_ACK_SIZE:
        packetType, nodeId, authorId, sequence = struct.unpack(
            POST_ACK_FORMAT,
            data,
        )
        if packetType != POST_ACK:
            raise ValueError("unknown social packet type")
        return POST_ACK, nodeId, sequence, None, authorId

    if len(data) < POST_HEADER_SIZE:
        raise ValueError("social packet is too short")
    if len(data) > POST_HEADER_SIZE + MAX_POST_BYTES:
        raise ValueError("social packet is too large")
    (
        packetType,
        senderId,
        authorId,
        sequence,
        createdAt,
        textLength,
    ) = struct.unpack(POST_FORMAT, data[:POST_HEADER_SIZE])
    if packetType != POST:
        raise ValueError("unknown social packet type")
    if not 1 <= textLength <= MAX_POST_BYTES:
        raise ValueError("post has an invalid text length")
    if len(data) != POST_HEADER_SIZE + textLength:
        raise ValueError("post length does not match its payload")
    try:
        text = data[POST_HEADER_SIZE:].decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("post text is not valid UTF-8") from error
    if "\0" in text:
        raise ValueError("post cannot contain a null character")
    return (
        POST,
        senderId,
        sequence,
        SocialPost(authorId, sequence, createdAt, text),
        None,
    )


class _SocialHandler(NetHandler):
    def __init__(self, socialNode:SocialNode):
        self._socialNode = socialNode

    async def handle(self, data:bytes, addr:tuple[str, int]) -> None:
        try:
            (
                packetType,
                senderId,
                sequence,
                post,
                acknowledgedAuthorId,
            ) = decodeSocialPacket(data)
        except ValueError as error:
            print(f"Ignored invalid social packet: {error}")
            return
        await self._socialNode.handlePacket(
            packetType,
            senderId,
            sequence,
            post,
            acknowledgedAuthorId,
            addr,
        )


class SocialNode:
    def __init__(
        self,
        host:str="0.0.0.0",
        bootstrapNodes:set[tuple[str, int]] | None=None,
        postIntervalSeconds:float=POST_INTERVAL_SECONDS,
        generatePosts:bool=True,
        onPost:Callable[[SocialPost], None] | None=None,
        onPeer:Callable[[PeerStatus], None] | None=None,
        onError:Callable[[str], None] | None=None,
    ):
        if postIntervalSeconds <= 0:
            raise ValueError("postIntervalSeconds must be greater than 0")
        self._runner = P4PRunner(netV4ListeningAddr=(host, 0))
        self._nodeGossiper = NodeGossiper(
            self._runner,
            syncIntervalSeconds=0.5,
            bootstrapNodes=bootstrapNodes or set(),
        )
        self._nodeId = self._runner.ed25519Signer.publicKey.publicKeyBytes
        self._postIntervalSeconds = postIntervalSeconds
        self._generatePosts = generatePosts
        self._onPost = onPost
        self._onPeer = onPeer
        self._onError = onError
        self._knownPosts:dict[tuple[bytes, int], None] = {}
        self._recentPosts:dict[tuple[bytes, int], SocialPost] = {}
        self._pendingPostsByPeer:dict[
            bytes,
            dict[tuple[bytes, int], tuple[SocialPost, float]],
        ] = {}
        self._lastSeen:dict[bytes, float] = {}
        self._peerStates:dict[bytes, bool] = {}
        self._tasks:list[asyncio.Task] = []
        self._stopEvent = asyncio.Event()
        self._runnerStarted = False
        self._heartbeatSequence = 0
        self._postSequence = 0
        if not self._runner.userNet.registerHandler(
            SOCIAL_UUID.bytes,
            _SocialHandler(self),
        ):
            raise RuntimeError("Unable to register the social network handler")

    @property
    def nodeId(self) -> bytes:
        return self._nodeId

    async def start(self) -> int:
        await self._runner.begin()
        self._runnerStarted = True
        await self._nodeGossiper.begin()
        self._tasks = [
            asyncio.create_task(self._heartbeatLoop()),
            asyncio.create_task(self._peerStatusLoop()),
        ]
        if self._generatePosts:
            self._tasks.append(asyncio.create_task(self._postLoop()))
        transport = self._runner.net._protocolV4.transport
        if transport is None:
            raise RuntimeError("Node failed to open its IPv4 socket")
        return int(transport.get_extra_info("sockname")[1])

    async def stop(self) -> None:
        self._stopEvent.set()
        for task in self._tasks:
            if not task.done():
                task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        if self._runnerStarted:
            await self._nodeGossiper.end()
            await self._runner.end()
            self._runnerStarted = False

    def _peerAddresses(self) -> dict[bytes, tuple[str, int]]:
        return {
            node.hashableEd25519PublicKey.publicKeyBytes: node.addr
            for node in self._nodeGossiper.nodeIdentifies
            if node.hashableEd25519PublicKey.publicKeyBytes != self._nodeId
        }

    def _send(self, data:bytes, address:tuple[str, int]) -> bool:
        packet = (
            itob(PacketFlag.USER, PacketElementSize.PACKET_FLAG)
            + SOCIAL_UUID.bytes
            + data
        )
        sent = self._runner.net.sendTo(packet, address)
        if not sent and self._onError is not None:
            self._onError(f"Unable to send social packet to {address[0]}:{address[1]}")
        return sent

    async def _heartbeatLoop(self) -> None:
        while not self._stopEvent.is_set():
            self._heartbeatSequence = (self._heartbeatSequence + 1) & 0xFFFFFFFF
            packet = encodeHeartbeat(self._nodeId, self._heartbeatSequence)
            peers = self._peerAddresses()
            for peerId, address in peers.items():
                self._send(packet, address)
                self._syncRecentPosts(peerId, address)
                self._retryPendingPosts(peerId, address)
            for peerId in set(self._pendingPostsByPeer) - set(peers):
                self._pendingPostsByPeer.pop(peerId, None)
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)

    async def _peerStatusLoop(self) -> None:
        while not self._stopEvent.is_set():
            now = time.monotonic()
            for nodeId, address in self._peerAddresses().items():
                lastSeen = self._lastSeen.get(nodeId)
                online = (
                    lastSeen is not None
                    and now - lastSeen < PEER_TIMEOUT_SECONDS
                )
                previousState = self._peerStates.get(nodeId)
                if previousState != online:
                    self._peerStates[nodeId] = online
                    if self._onPeer is not None:
                        self._onPeer(
                            PeerStatus(nodeId, address, online, lastSeen)
                        )
            await asyncio.sleep(1)

    async def _postLoop(self) -> None:
        await asyncio.sleep(1)
        while not self._stopEvent.is_set():
            self._postSequence = (self._postSequence + 1) & 0xFFFFFFFF
            recentPosts = sorted(
                self._recentPosts.values(),
                key=lambda item: (item.createdAt, item.authorId, item.sequence),
            )[-100:]
            post = generatePost(
                self._nodeId,
                self._postSequence,
                recentPosts=recentPosts,
            )
            self._rememberPost(post)
            if self._onPost is not None:
                self._onPost(post)
            for peerId, address in self._peerAddresses().items():
                self._sendPostToPeer(peerId, address, post)
            await asyncio.sleep(self._postIntervalSeconds)

    def _rememberPost(self, post:SocialPost) -> bool:
        if post.key in self._knownPosts:
            return False
        self._knownPosts[post.key] = None
        self._recentPosts[post.key] = post
        if len(self._knownPosts) > MAX_KNOWN_POSTS:
            oldestKey = next(iter(self._knownPosts))
            self._knownPosts.pop(oldestKey)
            self._recentPosts.pop(oldestKey, None)
            for pendingPosts in self._pendingPostsByPeer.values():
                pendingPosts.pop(oldestKey, None)
        if len(self._recentPosts) > MAX_RECENT_POSTS:
            oldestKey = next(iter(self._recentPosts))
            self._recentPosts.pop(oldestKey)
            for pendingPosts in self._pendingPostsByPeer.values():
                pendingPosts.pop(oldestKey, None)
        return True

    def _sendPostToPeer(
        self,
        peerId:bytes,
        address:tuple[str, int],
        post:SocialPost,
    ) -> None:
        pendingPosts = self._pendingPostsByPeer.setdefault(peerId, {})
        if post.key in pendingPosts:
            return
        while len(pendingPosts) >= MAX_PENDING_POSTS_PER_PEER:
            pendingPosts.pop(next(iter(pendingPosts)))
        pendingPosts[post.key] = (post, 0.0)

    def _retryPendingPosts(
        self,
        peerId:bytes,
        address:tuple[str, int],
    ) -> None:
        pendingPosts = self._pendingPostsByPeer.get(peerId, {})
        now = time.monotonic()
        sentCount = 0
        for postKey, (post, lastSentAt) in list(pendingPosts.items()):
            if (
                sentCount >= MAX_POST_RETRIES_PER_PEER_SYNC
                or now - lastSentAt < POST_RETRY_INTERVAL_SECONDS
            ):
                continue
            if self._send(encodePostPacket(self._nodeId, post), address):
                pendingPosts[postKey] = (post, now)
                sentCount += 1

    def _syncRecentPosts(
        self,
        peerId:bytes,
        address:tuple[str, int],
    ) -> None:
        recentPosts = sorted(
            self._recentPosts.values(),
            key=lambda post: (post.createdAt, post.authorId, post.sequence),
        )[-MAX_POSTS_PER_PEER_SYNC:]
        for post in recentPosts:
            self._sendPostToPeer(peerId, address, post)

    async def handlePacket(
        self,
        packetType:int,
        senderId:bytes,
        sequence:int,
        post:SocialPost | None,
        acknowledgedAuthorId:bytes | None,
        address:tuple[str, int],
    ) -> None:
        peerAddress = self._peerAddresses().get(senderId)
        if senderId == self._nodeId or peerAddress != address:
            return
        self._lastSeen[senderId] = time.monotonic()
        if not self._peerStates.get(senderId, False):
            self._peerStates[senderId] = True
            if self._onPeer is not None:
                self._onPeer(
                    PeerStatus(
                        senderId,
                        address,
                        True,
                        self._lastSeen[senderId],
                    )
                )
        if packetType == HEARTBEAT:
            return
        if packetType == POST_ACK and acknowledgedAuthorId is not None:
            pendingPosts = self._pendingPostsByPeer.get(senderId)
            if pendingPosts is not None:
                pendingPosts.pop((acknowledgedAuthorId, sequence), None)
            return
        if packetType != POST or post is None:
            return
        acknowledgement = encodePostAcknowledgement(
            self._nodeId,
            post.authorId,
            post.sequence,
        )
        self._send(acknowledgement, address)
        if not self._rememberPost(post):
            return
        if self._onPost is not None:
            self._onPost(post)
        for peerId, peer in self._peerAddresses().items():
            if peerId != senderId and peer != address:
                self._sendPostToPeer(peerId, peer, post)
