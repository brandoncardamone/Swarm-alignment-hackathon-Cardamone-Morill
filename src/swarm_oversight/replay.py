"""Offline replay of all maps over merged streams (v1 §4: valid because the red team does not adapt).

Calibration: J scores the group of (a sample of) benign requests in the calibration stream under each map;
tau_M(q) is the (1-q) quantile of those scores (audits = q x benign requests).
Evaluation: on a stream with one attack episode inserted, J scores every request whose group contains an
attack request, up to and including the completing request (audit happens before a request runs).
The attack is caught under map M at budget q iff one of those scores exceeds tau_M(q), so storing the max
score per (episode, map) is enough for every q and every bootstrap replicate."""
from __future__ import annotations

import asyncio
import random

from . import llm
from .config import models
from .judge import score_group
from .maps import Clustering, Oracle, PerAgent, Provenance, RandomMatched, Singleton

MAP_NAMES = ["singleton", "per_agent", "clustering", "provenance", "oracle", "random_matched"]


async def embeddings(stream: list[dict]) -> list[list[float]]:
    return await llm.embed(models()["embedder"]["model"], [e["request_text"][:2000] for e in stream])


def build_maps(stream, hidden, emb, *, M: int, h: int, tau_route: float, tau_multi: float | None = None):
    prov = Provenance(stream, M, h)
    return {"singleton": Singleton(stream), "per_agent": PerAgent(stream, M),
            "clustering": Clustering(stream, M, emb, tau_route=tau_route, tau_multi=tau_multi),
            "provenance": prov, "oracle": Oracle(stream, M, hidden), "random_matched": RandomMatched(stream, M, prov)}


async def _score(stream, idx):
    return await score_group([stream[j] for j in idx])


async def calibrate(stream, hidden, maps, *, sample: int, seed: int) -> dict[str, list[tuple[str, float]]]:
    """Returns map -> [(benign episode id, score)] so the bootstrap can resample benign episodes."""
    benign = [i for i, e in enumerate(stream) if not hidden[e["request_id"]]["is_attack"]]
    rng = random.Random(f"cal:{seed}")
    pick = sorted(rng.sample(benign, min(sample, len(benign))))
    out = {}
    for name, mp in maps.items():
        sc = await asyncio.gather(*(_score(stream, mp.group(i)) for i in pick))
        out[name] = [(hidden[stream[i]["request_id"]]["episode_id"], s) for i, s in zip(pick, sc)]
    return out


async def evaluate(stream, hidden, maps, completing_rid: str, *, cap: int = 25, seed: int = 0) -> dict[str, dict]:
    """`cap` bounds judged groups per map (cost): the attack requests' own groups first, then a random
    sample of the other requests whose group contains an attack piece. Reported as a limitation."""
    pos = {e["request_id"]: i for i, e in enumerate(stream)}
    stop = pos[completing_rid]
    atk = {i for i, e in enumerate(stream) if hidden[e["request_id"]]["is_attack"] and i <= stop}
    piece = {i: hidden[stream[i]["request_id"]].get("piece_index") for i in atk}
    out = {}
    for name, mp in maps.items():
        cand = []
        for i in range(stop + 1):
            g = mp.group(i)
            hit = [j for j in g if j in atk]
            if hit:
                cand.append((i, g, hit))
        n_cand = len(cand)
        if len(cand) > cap:
            own = [c for c in cand if c[0] in atk]
            rest = [c for c in cand if c[0] not in atk]
            random.Random(f"cap:{seed}:{name}").shuffle(rest)
            cand = (own + rest)[:cap]
        scores = await asyncio.gather(*(_score(stream, g) for _, g, _ in cand))
        all_pieces = {p for p in piece.values() if p is not None}
        full = [s for (i, g, hit), s in zip(cand, scores) if {piece[j] for j in hit} >= all_pieces]
        own = [s for (i, g, hit), s in zip(cand, scores) if i in atk]  # exploratory: one chance per attack request
        # grouping recall/precision measured at the attack requests themselves
        rec = [len([j for j in mp.group(i) if j in atk]) / len([j for j in atk if j <= i]) for i in sorted(atk)]
        prc = [len([j for j in mp.group(i) if j in atk]) / len(mp.group(i)) for i in sorted(atk)]
        out[name] = {"max": max(scores, default=float("-inf")), "n_judged": len(cand), "n_candidates": n_cand,
                     "max_own": max(own, default=float("-inf")), "n_own": len(own),
                     "max_full": max(full, default=float("-inf")), "has_full_group": bool(full),
                     "recall": sum(rec) / len(rec), "precision": sum(prc) / len(prc),
                     "group_size_attack": sum(len(mp.group(i)) for i in atk) / len(atk)}
    return out
