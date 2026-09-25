def split(data:bytes, *sizes:tuple[int], includeRest:bool = False) -> list[bytes]:
    """
    Split byte data into fixed-size segments.
    :param data: The source byte data to split.
    :param sizes: The sizes of each segment to extract.
    :param includeRest: Whether to append the remaining bytes after the fixed-size splits.
    :return: A list of the split byte segments, including the remaining bytes when requested.
    """
    if includeRest:
        data += b"\x00"
    splitData = []
    dataSize = len(data)
    head = 0
    
    for s in sizes:
        if head+s > dataSize:
            raise ValueError("Data too short")
        splitData.append(data[head:head+s])
        head += s
    if len(data) > head and includeRest:
        splitData.append(data[head:-1])

    return splitData