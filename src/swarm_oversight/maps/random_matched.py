import random


class RandomMatched:
    """Size control: a random set of earlier requests, the same size as i's provenance group."""
    name = "random_matched"

    def __init__(self, stream, M: int, provenance, seed: int = 0):
        self.prov, self.seed = provenance, seed

    def group(self, i: int) -> list[int]:
        k = len(self.prov.group(i)) - 1
        rng = random.Random(self.seed * 1_000_003 + i)
        return sorted(rng.sample(range(i), min(k, i))) + [i]
