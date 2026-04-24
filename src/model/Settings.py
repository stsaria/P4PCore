from threading import Lock

from model.Ed25519Signer import Ed25519Signer

class Settings:
    def __init__(self):
        self._v4ListeningAddr:tuple[str, int] = ("127.0.0.1", 25943)
        self._v6ListeningAddr:tuple[str, int] = ("::1", 25943)
        self._ed25519Signer:Ed25519Signer = Ed25519Signer()
        self._lock:Lock = Lock()
    @property
    def v4ListeningAddr(self) -> tuple[str, int] | None:
        with self._lock:
            return self._v4ListeningAddr
    @v4ListeningAddr.setter
    def v4ListeningAddr(self, addr:tuple[str, int]) -> None:
        with self._lock:
            self._v4ListeningAddr = addr
    @property
    def v6ListeningAddr(self) -> tuple[str, int] | None:
        with self._lock:
            return self._v6ListeningAddr
    @v6ListeningAddr.setter
    def v6ListeningAddr(self, addr:tuple[str, int]) -> None:
        with self._lock:
            self._v6ListeningAddr = addr
    @property
    def ed25519Signer(self) -> Ed25519Signer:
        with self._lock:
            return self._ed25519Signer
    @ed25519Signer.setter
    def ed25519Signer(self, signer:Ed25519Signer) -> None:
        with self._lock:
            self._ed25519Signer = signer