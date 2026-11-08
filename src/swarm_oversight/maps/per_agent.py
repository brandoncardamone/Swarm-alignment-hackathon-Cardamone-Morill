from collections import defaultdict

from .base import cut


class PerAgent:
    """The request and all earlier requests from its root (= attested lineage under independent roots)."""
    name = "per_agent"

    def __init__(self, stream, M: int):
        self.M, self.by_root, self.pos = M, defaultdict(list), {}
        for i, e in enumerate(stream):
            self.pos[i] = len(self.by_root[e["root_id"]])
            self.by_root[e["root_id"]].append(i)
        self.root = [e["root_id"] for e in stream]

    def group(self, i: int) -> list[int]:
        lst = self.by_root[self.root[i]]
        return cut(lst[: self.pos[i]], i, self.M)
