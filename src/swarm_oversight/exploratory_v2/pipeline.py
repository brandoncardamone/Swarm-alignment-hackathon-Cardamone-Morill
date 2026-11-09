"""EXPLORATORY planning, execution, linkage and piece-only judging."""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

from swarm_oversight.maps import Oracle, PerAgent, Singleton

from .design import background, episode, handoff, merge_steps
from .maps import PaddedPerAgent, Provenance, high_fanout_paths, integrity_flags, mentioned_stream
from .runtime import execute_stream


def protocol_hash(config: dict) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


def validate_config(config: dict) -> None:
    if config["analysis"] != "exploratory_v2" or config["M"] != 3 * config["cover_length"]:
        raise ValueError("v2 must be exploratory with M = 3L")
    if config["M"] < 1 or config["h"] < 1 or config["insertions"] < 1:
        raise ValueError("positive cap, hops and insertion count required")
    if not all(0 < q < 1 for q in config["qs"]) or config["primary_q"] not in config["qs"]:
        raise ValueError("invalid audit budgets")
    if config["output"] != "logs/exploratory_v2":
        raise ValueError("v2 outputs must stay separate from frozen outputs")


def make_maps(events: list[dict], hidden: dict, config: dict, calibration: list[dict]) -> dict:
    provenance = Provenance(events, config["M"], config["h"])
    return {"singleton": Singleton(events), "per_agent": PerAgent(events, config["M"]),
            "padded_per_agent": PaddedPerAgent(events, config["M"], provenance, config["seed"]),
            "provenance": provenance, "oracle": Oracle(events, config["M"], hidden),
            "path_mention": Provenance(mentioned_stream(events), config["M"], config["h"]),
            "fanout_capped": Provenance(events, config["M"], config["h"],
                                         high_fanout_paths(calibration, config["fanout_cap"]))}


def piece_positions(events: list[dict], hidden: dict, episode_id: str) -> list[int]:
    return [i for i, event in enumerate(events) if hidden[event["request_id"]]["episode_id"] == episode_id
            and hidden[event["request_id"]]["is_attack"]]


def linkage(events: list[dict], hidden: dict, spec: dict, maps: dict) -> dict:
    pieces = piece_positions(events, hidden, spec["id"])
    flags = integrity_flags(events)
    output = {}
    for name, mapper in maps.items():
        rows = []
        for i in pieces:
            group = set(mapper.group(i))
            raw = set(mapper.raw_group(i)) if hasattr(mapper, "raw_group") else group
            previous = {j for j in pieces if j <= i}
            target = maps["provenance"].group(i)
            rows.append({"position": i, "complete": previous <= group, "complete_uncapped": previous <= raw,
                         "precision": len(group & previous) / len(group), "size": len(group),
                         "no_link": not previous <= raw, "cut_by_cap": previous <= raw and not previous <= group,
                         "matched_size": len(group) == len(target),
                         "matched_roots": len({events[j]["root_id"] for j in group}) ==
                         len({events[j]["root_id"] for j in target})})
        output[name] = rows
    benign = [i for i, e in enumerate(events) if hidden[e["request_id"]]["episode_id"] != spec["id"]]
    output["integrity"] = {"caught": any(flags[i] for i in pieces), "benign_flags": sum(flags[i] for i in benign),
                           "benign_requests": len(benign)}
    return output


def measured_share(events: list[dict], hidden: dict, path: str, excluded: str | None = None) -> float:
    episodes, touched = set(), set()
    for event in events:
        eid = hidden[event["request_id"]]["episode_id"]
        if eid == excluded:
            continue
        episodes.add(eid)
        if path in event["paths_read"] + event["paths_written"]:
            touched.add(eid)
    return len(touched) / len(episodes) if episodes else 0.0


def build_world(config: dict, family: str, split: str, *, count: int | None = None) -> list[dict]:
    return background(family, count if count is not None else config["backgrounds"][split], split, config["seed"])


def execute_case(config: dict, world: list[dict], spec: dict, insertion: int, calibration: list[dict]) -> dict:
    # All routes/wordings of a task receive exactly the same benign ordering/insertion.
    seed = config["seed"] + 1009 * spec["index"] + insertion
    result = execute_stream(world + [spec], merge_steps(world, spec, seed), config["runner_image"])
    if result["failures"]:
        raise RuntimeError("tool failure in merged replay; inspect the isolated smoke case")
    maps = make_maps(result["events"], result["hidden"], config, calibration)
    return {"analysis": "exploratory_v2", "family": spec["family"], "task": spec["index"],
            "wording": spec["wording"], "route": spec["route"], "insertion": insertion,
            "completed": result["completed"][spec["id"]], "episode": spec["id"],
            "rho": measured_share(result["events"], result["hidden"], handoff(spec["family"], spec["route"]), spec["id"]),
            "linkage": linkage(result["events"], result["hidden"], spec, maps),
            "hop_sweep": {str(h): linkage(result["events"], result["hidden"], spec,
                                           {"provenance": Provenance(result["events"], config["M"], h)})["provenance"]
                          for h in range(1, 5)},
            "events": result["events"], "hidden": result["hidden"]}


def save_trace(path: Path, result: dict) -> None:
    """Keep hidden labels on disk separately, including intermediate exploratory artifacts."""
    path.mkdir(parents=True, exist_ok=True)
    (path / "exploratory_events.json").write_text(json.dumps(result["events"]))
    (path / "exploratory_hidden.json").write_text(json.dumps(result["hidden"]))
    metadata = {k: v for k, v in result.items() if k not in ("events", "hidden")}
    (path / "exploratory_metadata.json").write_text(json.dumps(metadata))


def attack_spec(config: dict, family: str, task: int, split: str, route: str, wording: str) -> dict:
    # Hashed job paths give both labels the same format; integer ranges are never exposed in paths.
    return episode(family, config["backgrounds"][split] + task, split, route,
                   malicious=True, chained=True, wording=wording)


async def score_pieces(case: dict, maps: dict, names: list[str]) -> dict:
    """Judge exactly the three piece requests; cover/benign audits never count."""
    from swarm_oversight.judge import score_group

    pieces = piece_positions(case["events"], case["hidden"], case["episode"])
    output = {}
    for name in names:
        scores = await asyncio.gather(*(score_group([case["events"][j] for j in maps[name].group(i)]) for i in pieces))
        output[name] = [{"position": i, "score": score} for i, score in zip(pieces, scores, strict=True)]
    return output
