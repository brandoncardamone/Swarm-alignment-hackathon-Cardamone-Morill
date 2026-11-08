def cut(idx, i: int, M: int) -> list[int]:
    """Keep i plus the most recent M-1 other earlier requests, in stream order."""
    others = sorted({j for j in idx if j < i})[-(M - 1):] if M > 1 else []
    return others + [i]
