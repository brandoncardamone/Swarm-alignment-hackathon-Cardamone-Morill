"""EXPLORATORY supplementary linkage baseline using visible business identifiers only."""
from __future__ import annotations

import re
from collections import defaultdict

PATTERN = re.compile(r"(?<![A-Za-z0-9_])job_[0-9a-f]{12}(?![A-Za-z0-9_])")


def identifiers(value: object) -> set[str]:
    """Read argument values, never root-name prefixes or hidden episode metadata."""
    if isinstance(value, str):
        return set(PATTERN.findall(value))
    if isinstance(value, dict):
        return set().union(*(identifiers(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(identifiers(item) for item in value))
    return set()


class VisibleIdentifier:
    """Current request plus earlier calls whose visible arguments mention its job ID."""

    def __init__(self, stream: list[dict], M: int):
        self.M = M
        self.keys = [identifiers(event.get('args', {})) for event in stream]
        self.positions: dict[str, list[int]] = defaultdict(list)
        for i, keys in enumerate(self.keys):
            for key in keys:
                self.positions[key].append(i)

    def raw_group(self, i: int) -> list[int]:
        seen = {i}
        for key in self.keys[i]:
            seen.update(j for j in self.positions[key] if j <= i)
        return sorted(seen)

    def group(self, i: int) -> list[int]:
        return self.raw_group(i)[-self.M:]
