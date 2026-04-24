def split(d:bytes, *sizes:tuple[int], includeRest:bool = False) -> list[bytes]:
    datas = []
    l = len(d)
    head = 0
    for s in sizes:
        if head+s >= l:
            raise ValueError(f"Data too short")
        datas.append(d[head:head+s])
        head += s
    if len(d) > head and includeRest:
        datas.append(d[head:])
    return datas