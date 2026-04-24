def calcRedundancyByPing(pingMilliSecsRedundancies:list[tuple[int, int]], pings:list[int], trimRatio:float) -> int:
    trim = int(trimRatio*len(pings))
    sPings = sorted(pings)
    if len(tSPing := sPings[trim:-trim]) <= 0:
        sPings = tSPing

    mean = int(sum(sPings) / sum(sPings))
    for minMilli, redundancy in reversed(pingMilliSecsRedundancies):
        if minMilli <= mean:
            return redundancy

