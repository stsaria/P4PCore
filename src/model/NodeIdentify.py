from dataclasses import dataclass

from src.model.HashableEd25519PublicKey import HashableEd25519PublicKey

@dataclass(frozen=True, kw_only=True)
class NodeIdentify:
    ip:str
    port:int
    hashableEd25519PublicKey:HashableEd25519PublicKey
    def __hash__(self) -> int:
        return hash((self.ip, self.port, self.hashableEd25519PublicKey.public_bytes_raw()))
    def __eq__(self, obj:"NodeIdentify") -> bool:
        if not isinstance(obj, NodeIdentify):
            return NotImplemented
        return (
            self.ip == obj.ip and
            self.port == obj.port and
            self.hashableEd25519PublicKey.public_bytes_raw() == obj.hashableEd25519PublicKey.public_bytes_raw()
        )
    @property
    def addr(self) -> tuple[str, int]:
        return self.ip, self.port
