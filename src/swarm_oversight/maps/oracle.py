from collections import defaultdict

from .base import cut


class Oracle:
    """Ceiling. Attack request: all K roots' requests of its episode so far. Benign: its own episode.
    Uses hidden episode labels, so it is not deployable."""
    name = "oracle"

    def __init__(self, stream, M: int, hidden):
        self.M = M
        self.ep = [hidden[e["request_id"]]["episode_id"] for e in stream]
        self.by_ep = defaultdict(list)
        for i, ep in enumerate(self.ep):
            self.by_ep[ep].append(i)

    def group(self, i: int) -> list[int]:
        return cut([j for j in self.by_ep[self.ep[i]] if j < i], i, self.M)
