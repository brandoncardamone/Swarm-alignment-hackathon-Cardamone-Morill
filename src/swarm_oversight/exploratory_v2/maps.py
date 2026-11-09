"""EXPLORATORY prefix-only maps. Deployable maps receive visible events only."""
from __future__ import annotations

import random
import re
from collections import defaultdict


class Provenance:
    """Follow earlier writers backwards; all traversed links respect stream time."""

    def __init__(self, stream: list[dict], M: int, h: int, ignored: set[str] | None = None):
        self.stream, self.M, self.h = stream, M, h
        self.parents: list[set[int]] = []
        writers: dict[str, set[int]] = defaultdict(set)
        for i, event in enumerate(stream):
            paths = (set(event["paths_read"]) | set(event["paths_written"])) - (ignored or set())
            self.parents.append(set().union(*(writers[p] for p in paths)))
            for path in set(event["paths_written"]) - (ignored or set()):
                writers[path].add(i)

    def raw_group(self, i: int) -> list[int]:
        seen, frontier = {i}, {i}
        for _ in range(self.h):
            frontier = set().union(*(self.parents[j] for j in frontier)) - seen
            seen.update(frontier)
        return sorted(seen)

    def group(self, i: int) -> list[int]:
        return self.raw_group(i)[-self.M:]


class PaddedPerAgent:
    """Preserve own history, then match provenance size/root count when feasible.

    Infeasible targets retain own history and report the mismatch; never silently
    drop own history to make this control look matched.
    """

    def __init__(self, stream: list[dict], M: int, provenance: Provenance, seed: int):
        self.stream, self.M, self.provenance, self.seed = stream, M, provenance, seed

    def group(self, i: int) -> list[int]:
        root = self.stream[i]["root_id"]
        own = [j for j in range(i + 1) if self.stream[j]["root_id"] == root][-self.M:]
        target = self.provenance.group(i)
        size = max(len(own), len(target))
        n_roots = len({self.stream[j]["root_id"] for j in target})
        rng = random.Random(f"exploratory-padding:{self.seed}:{i}")
        by_root: dict[str, list[int]] = defaultdict(list)
        for j in range(i):
            if self.stream[j]["root_id"] != root:
                by_root[self.stream[j]["root_id"]].append(j)
        roots = sorted(by_root)
        rng.shuffle(roots)
        chosen = roots[:min(n_roots - 1, size - len(own))]
        extra = [rng.choice(by_root[r]) for r in chosen]
        remaining = [j for r in chosen for j in by_root[r] if j not in extra]
        extra += rng.sample(remaining, min(len(remaining), size - len(own) - len(extra)))
        return sorted(own + extra)


def mentioned_stream(stream: list[dict]) -> list[dict]:
    """A path is text-visible only if its literal canonical spelling is present."""
    known = {p for e in stream for p in e["paths_read"] + e["paths_written"]}
    # The vocabulary contains no labels. Literal boundaries prevent x.py matching x.py.bak.
    patterns = {p: re.compile(r"(?<![\w/.-])" + re.escape(p) + r"(?![\w/.-])") for p in known}
    return [{**e, "paths_read": [p for p in e["paths_read"] if patterns[p].search(e["request_text"])],
             "paths_written": [p for p in e["paths_written"] if patterns[p].search(e["request_text"])]}
            for e in stream]


def high_fanout_paths(calibration: list[dict], cap: int) -> set[str]:
    roots: dict[str, set[str]] = defaultdict(set)
    for event in calibration:
        for path in event["paths_read"] + event["paths_written"]:
            roots[path].add(event["root_id"])
    return {p for p, touched in roots.items() if len(touched) > cap}


def integrity_flags(stream: list[dict]) -> list[bool]:
    """Cross-root dependency into execution, registration or config writes."""
    writers: dict[str, str] = {}
    flags = []
    for event in stream:
        relevant = event["tool"] in ("run", "register_step") or any(
            p.startswith("config/") for p in event["paths_written"])
        flags.append(relevant and any(writers.get(p, event["root_id"]) != event["root_id"]
                                     for p in event["paths_read"]))
        for path in event["paths_written"]:
            writers[path] = event["root_id"]
    return flags
