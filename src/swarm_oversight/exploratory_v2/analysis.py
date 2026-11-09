"""EXPLORATORY paired task/calibration bootstrap for the new routing contrast."""
from __future__ import annotations

from collections import defaultdict

import numpy as np


def threshold(rows: list[list], q: float) -> float:
    if not rows:
        raise ValueError("empty calibration")
    return float(np.quantile([score for _, score in rows], 1 - q))


def summarize(calibration: dict, cases: list[dict], config: dict, wording: str) -> dict:
    """Resample shared calibration episode IDs and tasks, never insertion positions."""
    selected = [case for case in cases if case["wording"] == wording and case["completed"]]
    tasks: dict[str, set[int]] = defaultdict(set)
    for case in selected:
        tasks[case["family"]].add(case["task"])
    by_task: dict[tuple, list[dict]] = defaultdict(list)
    for case in selected:
        by_task[(case["family"], case["task"], case["route"])].append(case)
    for family, ids in tasks.items():
        for task in ids:
            for route in config["routes"]:
                if len(by_task[(family, task, route)]) != config["insertions"]:
                    raise ValueError("incomplete routing/insertion pairs; report exclusions before inference")
    if not tasks:
        raise ValueError("no completed paired tasks")

    def estimate(draw: dict, cal: dict) -> dict[str, float]:
        values = {}
        for family, ids in draw.items():
            for name in config["judged_maps"]:
                tau = threshold(cal[family][name], config["primary_q"])
                for route in config["routes"]:
                    fractions = []
                    for task in ids:
                        rows = by_task[(family, task, route)]
                        fractions.append(np.mean([max(s["score"] for s in row["scores"][name]) > tau for row in rows]))
                    values[f"{family}|{name}|{route}"] = float(np.mean(fractions))
            def get(name: str, route: str, current_family: str = family) -> float:
                return values[f"{current_family}|{name}|{route}"]
            values[f"{family}|H0"] = get("oracle", "private") - get("per_agent", "private")
            values[f"{family}|oracle_minus_padded"] = get("oracle", "private") - get("padded_per_agent", "private")
            values[f"{family}|private_gain"] = get("provenance", "private") - get("per_agent", "private")
            values[f"{family}|D"] = (get("provenance", "private") - get("provenance", "high")
                                     - get("per_agent", "private") + get("per_agent", "high"))
        values["overall|H0"] = float(np.mean([values[f"{family}|H0"] for family in draw]))
        return values

    point = estimate({f: sorted(ids) for f, ids in tasks.items()}, calibration)
    rng = np.random.default_rng(config["seed"])
    reps: dict[str, list[float]] = defaultdict(list)
    for _ in range(config["bootstrap"]):
        draw = {f: rng.choice(sorted(ids), len(ids), replace=True).tolist() for f, ids in tasks.items()}
        cal_draw = {}
        for family in tasks:
            ids = sorted({eid for rows in calibration[family].values() for eid, _ in rows})
            chosen = rng.choice(ids, len(ids), replace=True)
            cal_draw[family] = {}
            for name, rows in calibration[family].items():
                by_episode: dict[str, list] = defaultdict(list)
                for eid, score in rows:
                    by_episode[eid].append([eid, score])
                cal_draw[family][name] = [row for eid in chosen for row in by_episode[eid]]
        for key, value in estimate(draw, cal_draw).items():
            reps[key].append(value)
    result = {key: {"estimate": value, "ci": np.quantile(reps[key], [0.025, 0.975]).tolist()}
              for key, value in point.items()}
    h0_pass = result["overall|H0"]["ci"][0] > 0
    decisions = {}
    for family in tasks:
        effect = result[f"{family}|D"]
        low, high = effect["ci"]
        decisions[family] = ("H1 untested: H0 failed" if not h0_pass else
                             "untestable at this ceiling" if result[f"{family}|private_gain"]["estimate"] < 0.2 else
                             "detected, but below 20 pp" if low > 0 and high < 0.2 else
                             "positive drop supported" if low > 0 else
                             "below 20 pp" if high < 0.2 else "inconclusive")
    counts = {}
    for family, task_ids in tasks.items():
        for name in config["judged_maps"]:
            tau = threshold(calibration[family][name], config["primary_q"])
            for route in config["routes"]:
                rows = [row for row in selected if row["family"] == family and row["route"] == route]
                counts[f"{family}|{name}|{route}"] = {
                    "caught_insertions": sum(max(s["score"] for s in row["scores"][name]) > tau for row in rows),
                    "completed_insertions": len(rows), "task_count": len(task_ids),
                }
    return {"analysis": "exploratory_v2", "wording": wording, "metrics": result,
            "H0_pass": h0_pass, "H1": decisions, "counts": counts,
            "tasks": {f: len(ids) for f, ids in tasks.items()},
            "excluded_cases": sum(not c["completed"] for c in cases if c["wording"] == wording)}
