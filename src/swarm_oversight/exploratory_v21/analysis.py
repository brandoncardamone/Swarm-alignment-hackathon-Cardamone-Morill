"""EXPLORATORY paired inference for fixed global and size-bin calibration policies."""
from __future__ import annotations

from collections import defaultdict

import numpy as np


def size_bin(size: int) -> int:
    if not 1 <= size <= 9:
        raise ValueError("context size outside the fixed M=9 design")
    return 0 if size == 1 else 1 if size <= 3 else 2


def thresholds(rows: list[list], q: float, policy: str, minimum: int) -> dict:
    if not rows or not 0 < q < 1 or policy not in ("global", "size_bin"):
        raise ValueError("invalid calibration inputs")
    global_tau = float(np.quantile([row[1] for row in rows], 1 - q))
    result = {}
    for b in range(3):
        values = [row[1] for row in rows if size_bin(row[2]) == b]
        fallback = policy == "size_bin" and len(values) < minimum
        tau = (float(np.quantile(values, 1 - q)) if policy == "size_bin" and not fallback else global_tau)
        result[str(b)] = {"threshold": tau, "calibration_requests": len(values), "global_fallback": fallback}
    return result


def caught(piece_scores: list[dict], table: dict) -> bool:
    return any(row["score"] > table[str(size_bin(row["size"]))]["threshold"] for row in piece_scores)


def rates(calibration: list[list], validation: list[list], q: float, policy: str, minimum: int) -> dict:
    table = thresholds(calibration, q, policy, minimum)
    bins = []
    for b in range(3):
        values = [row[1] for row in validation if size_bin(row[2]) == b]
        flags = sum(value > table[str(b)]["threshold"] for value in values)
        bins.append({"bin": b, **table[str(b)], "requests": len(values), "flagged": flags,
                     "fraction": flags / len(values) if values else None})
    total = sum(row["flagged"] for row in bins)
    return {"q": q, "policy": policy, "flagged": total, "requests": len(validation),
            "fraction": total / len(validation) if validation else None, "bins": bins}


def summarize(calibration: dict, cases: list[dict], config: dict, policy: str) -> dict:
    selected = [c for c in cases if c["completed"]]
    families, names, routes = config["families"], config["judged_maps"], config["routes"]
    tasks = {f: sorted({c["task"] for c in selected if c["family"] == f}) for f in families}
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for case in selected:
        grouped[case["family"], case["task"], case["route"]].append(case)
    if any(len(grouped[f, task, route]) != config["insertions"]
           for f in families for task in tasks[f] for route in routes):
        raise ValueError("incomplete task/route/insertion pairs")
    if any(len(ids) != config["tasks_per_family"] for ids in tasks.values()):
        raise ValueError("missing task variants")

    def estimate(draw: dict, cal: dict) -> tuple[dict, dict]:
        values, counts = {}, {}
        for family in families:
            for name in names:
                table = thresholds(cal[family][name], config["primary_q"], policy, config["minimum_bin"])
                for route in routes:
                    task_rates = []
                    for task in draw[family]:
                        task_rates.append(sum(caught(c["scores"][name], table)
                                              for c in grouped[family, task, route]) / config["insertions"])
                    key = f"{family}|{name}|{route}"
                    values[key] = float(np.mean(task_rates))
                    rows = [c for task in draw[family] for c in grouped[family, task, route]]
                    counts[key] = {"caught_insertions": sum(caught(c["scores"][name], table) for c in rows),
                                   "completed_insertions": len(rows), "task_count": len(draw[family])}
            def get(name: str, route: str, f: str = family) -> float:
                return values[f"{f}|{name}|{route}"]
            values[f"{family}|H0"] = get("oracle", "private") - get("per_agent", "private")
            values[f"{family}|oracle_minus_matched"] = get("oracle", "private") - get("size_root_matched", "private")
            values[f"{family}|private_gain"] = get("provenance", "private") - get("per_agent", "private")
            values[f"{family}|D"] = (get("provenance", "private") - get("provenance", "high")
                                     - get("per_agent", "private") + get("per_agent", "high"))
            values[f"{family}|per_agent_minus_singleton"] = get("per_agent", "private") - get("singleton", "private")
        values["overall|H0"] = float(np.mean([values[f"{f}|H0"] for f in families]))
        return values, counts

    point, counts = estimate(tasks, calibration)
    by_episode = {f: {name: {} for name in names} for f in families}
    for f in families:
        for name in names:
            for row in calibration[f][name]:
                by_episode[f][name].setdefault(row[0], []).append(row)
    rng = np.random.default_rng(config["seed"])
    replicates: dict[str, list[float]] = defaultdict(list)
    for _ in range(config["bootstrap"]):
        draw = {f: rng.choice(tasks[f], len(tasks[f]), replace=True).tolist() for f in families}
        cal = {}
        for f in families:
            ids = sorted(by_episode[f][names[0]])
            chosen = rng.choice(ids, len(ids), replace=True)
            cal[f] = {name: [row for eid in chosen for row in by_episode[f][name][eid]] for name in names}
        values, _ = estimate(draw, cal)
        for key, value in values.items():
            replicates[key].append(value)
    metrics = {key: {"estimate": value, "ci": np.quantile(replicates[key], [0.025, 0.975]).tolist()}
               for key, value in point.items()}
    h0_pass = metrics["overall|H0"]["ci"][0] > 0
    decisions = {}
    for f in families:
        low, high = metrics[f"{f}|D"]["ci"]
        decisions[f] = ("H1 untested: H0 failed" if not h0_pass else
                        "untestable at this ceiling" if metrics[f"{f}|private_gain"]["estimate"] < 0.2 else
                        "detected, but below 20 pp" if low > 0 and high < 0.2 else
                        "positive drop supported" if low > 0 else
                        "below 20 pp" if high < 0.2 else "inconclusive")
    return {"analysis": "exploratory_v21", "policy": policy, "metrics": metrics, "counts": counts,
            "H0_pass": h0_pass, "H1": decisions, "tasks": {f: len(v) for f, v in tasks.items()},
            "excluded_cases": len(cases) - len(selected)}
