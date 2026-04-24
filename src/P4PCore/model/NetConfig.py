from dataclasses import dataclass

@dataclass(kw_only=True)
class NetConfig:
    addrV4:tuple[str, int]
    addrV6:tuple[str, int]