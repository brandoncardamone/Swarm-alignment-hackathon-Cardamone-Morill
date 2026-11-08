"""Regenerate RESULTS_LIVE.md: a live view of rollouts, experiment progress, spend and interim results.

Interim safety = point estimates (no bootstrap) on whatever (family, overlap) blocks have finished so far.
They are NOT the final results: CIs, the full grid and hypothesis tests come from scripts/analyze.py."""
import json
import time
from collections import Counter, defaultdict

import httpx
import numpy as np
import yaml

from swarm_oversight.config import LOG_DIR, ROOT, api_key
from swarm_oversight.stats import safety_table, tau

OUT = ROOT / "RESULTS_LIVE.md"
P = yaml.safe_load((ROOT / "configs" / "frozen.yaml").read_text())
MAPS = ["singleton", "per_agent", "clustering", "provenance", "random_matched", "oracle"]
NAME = {"singleton": "Singleton", "per_agent": "Per-agent (baseline)", "clustering": "Clustering (provider)",
        "provenance": "Provenance (harness)", "random_matched": "Random size-matched", "oracle": "Oracle (ceiling)"}


def spend():
    try:
        d = httpx.get("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {api_key('openrouter')}"},
                      timeout=15).json()["data"]
        return f"${d['usage']:.2f}"
    except Exception:  # noqa: BLE001
        return "unavailable"


def main():
    L = [f"# Live results tracker\n\n_Last updated: {time.strftime('%a %b %d, %H:%M:%S %Z')}_ · regenerated every 2 min "
         f"while the experiment runs (`scripts/live_status.py`). Interim numbers are point estimates on finished blocks "
         f"only; final numbers with CIs come from `scripts/analyze.py` → `logs/results/summary.md`.\n"]
    L.append(f"**OpenRouter spend:** {spend()} of $20\n")

    # rollouts
    metas = [json.loads(p.read_text()) for p in (LOG_DIR / "episodes").glob("*.json")]
    atk = [m for m in metas if m["kind"] == "attack" and m["split"] == "eval"]
    ben = [m for m in metas if m["kind"] == "benign" and m["split"] == "pool"]
    L.append("## 1. Rollouts\n")
    L.append(f"- Attack episodes: **{len(atk)}/72** ran, **{sum(m['completed'] for m in atk)}** completed the proxy harm "
             f"unmonitored (others excluded, per v1).")
    by = Counter((m["family"], m["attack"]) for m in atk if m["completed"])
    L.append("  - Completed by family × attack: " + ", ".join(f"{f}/{a}: {n}" for (f, a), n in sorted(by.items())))
    L.append(f"- Benign pool: **{len(ben)}/600** episodes; chained across roots: {sum(m['chained'] for m in ben)}.")
    for f in ("audit_off", "label_poison", "config_backdoor"):
        L.append(f"  - touching `{f}` artifacts: {sum(f in m['touches'] for m in ben)}")

    # experiment progress
    L.append("\n## 2. Experiment progress (frozen protocol)\n")
    exp = (LOG_DIR / "experiment.txt")
    lines = exp.read_text().splitlines() if exp.exists() else []
    blocks = [ln for ln in lines if ln.startswith("[")]
    L.append(f"- Blocks finished: **{sum('evaluated' in b for b in blocks)}/6** (3 families × 2 overlap levels).")
    L.append("```\n" + ("\n".join(lines[-8:]) if lines else "(not started)") + "\n```")

    # interim results
    R = LOG_DIR / "results"
    if (R / "ev.json").exists() and (R / "cal.json").exists():
        cal_raw, ev = json.loads((R / "cal.json").read_text()), json.loads((R / "ev.json").read_text())
        cal = {}
        for k, rows in cal_raw.items():
            f, o, m = k.split("|")
            cal[(f, float(o), m)] = rows
        for r in ev:
            r["overlap"] = float(r["overlap"])
        ev = [r for r in ev if (r["family"], r["overlap"], r["map"]) in cal]
        if ev:
            ovs = sorted({r["overlap"] for r in ev})
            T = safety_table(cal, ev, [P["primary_q"]], boot=0, maps=MAPS, overlaps=ovs)
            fams = sorted({r["family"] for r in ev})
            n_ep = len({r["episode"] for r in ev})
            L.append(f"\n## 3. Interim results at q = {100 * P['primary_q']:g}% (families so far: {', '.join(fams)}; "
                     f"{n_ep} attack episodes)\n")
            L.append("| Overlap | Map | Safety A0 | A1 | A2 | **Worst case** | Grouping recall | Mean group size |")
            L.append("|---|---|---|---|---|---|---|---|")
            for o in ovs:
                for m in MAPS:
                    if (m, o, P["primary_q"]) not in T:
                        continue
                    t = T[(m, o, P["primary_q"])]
                    rs = [r for r in ev if r["map"] == m and r["overlap"] == o]
                    sa = t["S_by_attack"]
                    f = (lambda v: "–" if np.isnan(v) else f"{100 * v:.0f}%")
                    L.append(f"| {int(100 * o)}% | {NAME[m]} | {f(sa.get('A0', float('nan')))} | "
                             f"{f(sa.get('A1', float('nan')))} | {f(sa.get('A2', float('nan')))} | "
                             f"**{f(t['S_worst'])}** | {np.mean([r['recall'] for r in rs]):.2f} | "
                             f"{np.mean([r['group_size_attack'] for r in rs]):.1f} |")
            # quick read on the hypotheses (point estimates only)
            L.append("\n**Interim hypothesis read (point estimates; no CIs yet):**")
            q = P["primary_q"]
            for o in ovs:
                if ("oracle", o, q) in T and ("per_agent", o, q) in T:
                    d = T[("oracle", o, q)]["S_worst"] - T[("per_agent", o, q)]["S_worst"]
                    L.append(f"- H0 @ {int(100 * o)}%: oracle − per-agent = {100 * d:+.0f} pp")
            lo = min(ovs)
            if ("provenance", lo, q) in T:
                d = T[("provenance", lo, q)]["S_worst"] - T[("clustering", lo, q)]["S_worst"]
                L.append(f"- H-main @ {int(100 * lo)}%: provenance − clustering = {100 * d:+.0f} pp (MEI 20 pp)")
            if len(ovs) > 1:
                d = T[("provenance", min(ovs), q)]["S_worst"] - T[("provenance", max(ovs), q)]["S_worst"]
                L.append(f"- H-dilution: provenance(10%) − provenance(40%) = {100 * d:+.0f} pp")
            # judge separation
            ben_sc = defaultdict(list)
            for (f, o, m), rows in cal.items():
                ben_sc[m] += [s for _, s in rows]
            L.append("\n**Judge thresholds τ at q = 2% (calibration, pooled):** " + ", ".join(
                f"{m}: {tau(np.array(v), q):.2f}" for m, v in ben_sc.items()))
    else:
        L.append("\n## 3. Interim results\n\n_No finished blocks yet. The first appears after one family's calibration and "
                 "evaluation at one overlap level._")

    # dev reference
    L.append("\n## 4. Reference: dev pilot (frozen judge, 9 dev attacks, 60 dev benign)\n")
    L.append("Oracle caught 5/9, per-agent 2/9, singleton 3/9 at q = 2% (`logs/pilot_run2.txt`). "
             "Dev tuning (`logs/tune_dev.json`): clustering θ = 0.80 → recall 0.66, group 13.0; "
             "provenance h = 2 → recall 0.63, group 12.9.")
    OUT.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
