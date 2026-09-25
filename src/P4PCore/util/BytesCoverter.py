from enum import IntEnum

from P4PCore.protocol.Protocol import ENDIAN, STR_ENCODING

def itob(i:int | IntEnum, size:int, endian:str=ENDIAN, signed:bool=False) -> bytes:
    """
    Convert an integer value to bytes.
    :param i: The integer or IntEnum value to encode.
    :param size: The number of bytes in the output.
    :param endian: The byte order used for encoding.
    :param signed: Whether the value should be treated as signed.
    :return: The integer encoded as bytes.
    """
    return (i.value if isinstance(i, IntEnum) else i).to_bytes(size, endian, signed=signed)

def btoi(bI:bytes, endian:str=ENDIAN, signed=False) -> int:
    """
    Convert bytes to an integer.
    :param bI: The byte sequence to decode.
    :param endian: The byte order used for decoding.
    :param signed: Whether the value should be treated as signed.
    :return: The decoded integer value.
    """
    return int.from_bytes(bI, endian, signed=signed)

def stob(s:str, size:int, encoding:str=STR_ENCODING) -> bytes:
    """
    Convert a string to fixed-size bytes.
    :param s: The string to encode.
    :param size: The target size in bytes; the result is padded with null bytes when needed.
    :param encoding: The character encoding used for conversion.
    :return: The encoded bytes padded to the requested size.
    """
    b = bytearray()
    for c in s:
        if size and len(b) + len(c.encode(encoding)) > size:
            break
        b.append(c.encode(encoding, errors="ignore")[0])
    return bytes(b)+(b"\x00"*(size-len(b)))

def btos(b:bytes, encoding:str=STR_ENCODING) -> str:
    """
    Convert bytes to a string.
    :param b: The byte sequence to decode.
    :param encoding: The character encoding used for decoding.
    :return: The decoded string without trailing null bytes.
    """
    return b.rstrip(b"\x00").decode(encoding, errors="ignore")