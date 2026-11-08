from collections import defaultdict, deque


class Provenance:
    """Harness-side map: requests within h hops of i in the path-level write -> read/write graph.

    Edge j -- k (j < k) iff j wrote a path that k later read or wrote. Only requests at positions <= i
    are visible when judging i. No time window. The group is cut to the most recent M (BFS order breaks
    ties toward nearer hops first, then recency)."""
    name = "provenance"

    def __init__(self, stream, M: int, h: int = 2):
        self.M, self.h = M, h
        self.adj = defaultdict(set)
        writers = defaultdict(list)
        for k, e in enumerate(stream):
            for p in set(e["paths_read"]) | set(e["paths_written"]):
                for j in writers[p]:
                    self.adj[k].add(j); self.adj[j].add(k)
            for p in e["paths_written"]:
                writers[p].append(k)

    def group(self, i: int) -> list[int]:
        seen, q = {i: 0}, deque([i])
        while q:
            u = q.popleft()
            if seen[u] == self.h:
                continue
            for v in self.adj[u]:
                if v <= i and v not in seen:
                    seen[v] = seen[u] + 1
                    q.append(v)
        # nearest hops first, then most recent; keep M-1 others
        others = sorted((j for j in seen if j != i), key=lambda j: (seen[j], -j))[: self.M - 1]
        return sorted(others) + [i]

    def raw_size(self, i: int) -> int:
        return len(self.group(i))
