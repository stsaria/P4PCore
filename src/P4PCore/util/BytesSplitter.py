def split(data:bytes, *sizes:tuple[int], includeRest:bool = False) -> list[bytes]:
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