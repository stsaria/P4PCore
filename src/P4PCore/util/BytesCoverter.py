from enum import IntEnum

from P4PCore.protocol.Protocol import ENDIAN, STR_ENCODING

def itob(i:int | IntEnum, size:int, endian:str=ENDIAN, signed:bool=False) -> bytes:
    return (i.value if isinstance(i, IntEnum) else i).to_bytes(size, endian, signed=signed)

def btoi(bI:bytes, endian:str=ENDIAN, signed=False) -> int:
    return int.from_bytes(bI, endian, signed=signed)

def stob(s:str, size:int, encoding:str=STR_ENCODING) -> bytes:
    b = bytearray()
    for c in s:
        if size and len(b) + len(c.encode(encoding)) > size:
            break
        b.append(c.encode(encoding, errors="ignore")[0])
    return bytes(b)+(b"\x00"*(size-len(b)))

def btos(b:bytes, encoding:str=STR_ENCODING) -> str:
    return b.rstrip(b"\x00").decode(encoding, errors="ignore")