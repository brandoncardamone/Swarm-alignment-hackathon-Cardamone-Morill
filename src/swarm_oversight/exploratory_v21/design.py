"""EXPLORATORY cover-first planning and a label-blind exact matched control."""
from __future__ import annotations

import copy
import random
from collections import defaultdict

from swarm_oversight.exploratory_v2.design import merge_steps
from swarm_oversight.exploratory_v2.maps import Provenance, high_fanout_paths, mentioned_stream
from swarm_oversight.maps import Oracle, PerAgent, Singleton


def cover_first(spec: dict) -> dict:
    """Reorder each fixed triple without using its labels to choose the order."""
    result = copy.deepcopy(spec)
    if len(spec["steps"]) != 9 or len(spec["labels"]) != 9:
        raise ValueError("expected three fixed operation/read/write triples")
    order = [base + offset for base in (0, 3, 6) for offset in (1, 0, 2)]
    result["steps"] = [result["steps"][i] for i in order]
    result["labels"] = [result["labels"][i] for i in order]
    return result


def plan(benign: list[dict], attack: dict | None, seed: int) -> list[tuple[dict, dict]]:
    """Seed construction uses original specs; only the execution plan is reordered."""
    return merge_steps([cover_first(s) for s in benign], cover_first(attack) if attack else None, seed)


class SizeRootMatched:
    """Random prefix context matching size/roots, anchored on the current request.

    Unlike padded per-agent, it does not promise to retain own-root history.
    A capacity fallback chooses the largest available root histories if a random
    root subset cannot supply the target size. No episode labels are accepted.
    """

    def __init__(self, stream: list[dict], target: Provenance, seed: int):
        self.stream, self.target, self.seed = stream, target, seed
        self.fallbacks: dict[int, bool] = {}

    def group(self, i: int) -> list[int]:
        target = self.target.group(i)
        size = len(target)
        roots_needed = len({self.stream[j]["root_id"] for j in target})
        current = self.stream[i]["root_id"]
        by_root: dict[str, list[int]] = defaultdict(list)
        for j in range(i + 1):
            by_root[self.stream[j]["root_id"]].append(j)
        others = sorted(root for root in by_root if root != current)
        rng = random.Random(f"exploratory-v21-matched:{self.seed}:{i}")
        rng.shuffle(others)
        selected = others[:roots_needed - 1]
        fallback = len(by_root[current]) + sum(len(by_root[r]) for r in selected) < size
        if fallback:
            selected = sorted(others, key=lambda r: len(by_root[r]), reverse=True)[:roots_needed - 1]
        self.fallbacks[i] = fallback
        chosen = [i] + [rng.choice(by_root[root]) for root in selected]
        pool = [j for root in [current, *selected] for j in by_root[root] if j not in chosen]
        if len(pool) < size - len(chosen):
            raise ValueError("target context is not feasible in its own prefix")
        chosen += rng.sample(pool, size - len(chosen))
        return sorted(chosen)


def make_maps(events: list[dict], hidden: dict, config: dict, calibration: list[dict]) -> dict:
    provenance = Provenance(events, config["M"], config["h"])
    return {"singleton": Singleton(events), "per_agent": PerAgent(events, config["M"]),
            "size_root_matched": SizeRootMatched(events, provenance, config["seed"]),
            "provenance": provenance, "oracle": Oracle(events, config["M"], hidden),
            "path_mention": Provenance(mentioned_stream(events), config["M"], config["h"]),
            "fanout_capped": Provenance(events, config["M"], config["h"],
                                        high_fanout_paths(calibration, config["fanout_cap"]))}
