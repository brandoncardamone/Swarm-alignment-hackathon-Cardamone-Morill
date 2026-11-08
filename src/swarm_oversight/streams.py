"""Build merged request streams (v1 §4).

For each (attack family f, overlap level o) we draw two disjoint backgrounds of benign episodes from the pool:
calibration and evaluation, each with a fraction o of episodes that touch f's artifacts. Episodes are merged
request by request at a fixed simulated concurrency: each episode gets a random start time and its requests
follow at unit spacing in their logged order, so causal order within an episode is kept. Each evaluation
stream gets exactly one attack episode, inserted at a random position. Links between episodes come only
from canonical shared paths in the merged log."""
from __future__ import annotations

import json
import random
from pathlib import Path

from .config import LOG_DIR
from .gateway import load_episode

CONCURRENCY = 20


def load_meta(log_dir: Path = LOG_DIR) -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text()) for p in (log_dir / "episodes").glob("*.json")}


def episode_requests(eid: str, log_dir: Path = LOG_DIR) -> tuple[list[dict], dict]:
    evs, hid = load_episode(log_dir, eid)
    return evs, {h["request_id"]: h for h in hid}


def draw_backgrounds(pool: list[dict], family: str, overlap: float, n: int, seed: int) -> tuple[list[str], list[str]]:
    rng = random.Random(f"bg:{family}:{overlap}:{seed}")
    touch = [m["episode_id"] for m in pool if family in m["touches"]]
    other = [m["episode_id"] for m in pool if family not in m["touches"]]
    rng.shuffle(touch)
    rng.shuffle(other)
    nt = round(overlap * n)
    if 2 * nt > len(touch) or 2 * (n - nt) > len(other):
        raise ValueError(f"pool too small for {family} @ {overlap}: touch={len(touch)} other={len(other)} n={n}")
    cal = touch[:nt] + other[: n - nt]
    ev = touch[nt: 2 * nt] + other[n - nt: 2 * (n - nt)]
    return cal, ev


def merge(episodes: list[str], seed: int, attack: str | None = None, log_dir: Path = LOG_DIR):
    """Return (stream, hidden): stream = visible event dicts in merged order with stream_position set."""
    rng = random.Random(f"merge:{seed}:{attack}")
    reqs, hidden = {}, {}
    for e in episodes + ([attack] if attack else []):
        evs, hid = episode_requests(e, log_dir)
        reqs[e] = evs
        hidden.update(hid)
    total = sum(len(v) for v in reqs.values())
    horizon = max(1.0, total / CONCURRENCY)
    timed = []
    for e, evs in reqs.items():
        t0 = rng.uniform(0, horizon)
        for j, ev in enumerate(evs):
            timed.append((t0 + j, rng.random(), ev))
    timed.sort(key=lambda x: (x[0], x[1]))
    stream = []
    for pos, (_, _, ev) in enumerate(timed):
        v = {k: ev[k] for k in ("request_id", "root_id", "request_text", "tool", "paths_read", "paths_written")}
        v["stream_position"] = pos
        stream.append(v)
    return stream, hidden
