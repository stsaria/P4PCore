from src.core.Net import Net


class NetRecvedEvent:
    def __init__(self, net:Net, data:bytes, addr:tuple[str, int]):
        self._net = net
        self._data = data
        self._addr = addr
        self._cancel = False
    @property
    def net(self) -> Net:
        return self._net
    @property
    def data(self) -> bytes:
        return self._data
    @property
    def addr(self) -> tuple[str, int]:
        return self._addr
    def cancel(self) -> None:
        self._cancel = True
    @property
    def isCanceled(self) -> bool:
        return self._cancel