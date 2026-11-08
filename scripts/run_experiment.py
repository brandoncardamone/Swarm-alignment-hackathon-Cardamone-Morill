"""Offline replay of the frozen protocol over all streams; writes logs/results/{cal,ev}.json.

Frozen parameters live in configs/frozen.yaml (committed before evaluation = pre-registration)."""
import asyncio
import json
import os

import yaml

from swarm_oversight import llm
from swarm_oversight.config import LOG_DIR, ROOT
from swarm_oversight.replay import build_maps, calibrate, embeddings, evaluate
from swarm_oversight.streams import draw_backgrounds, load_meta, merge
from tasks.attacks.ATTACK_TEMPLATES_proxy_goals import FAMILIES

P = yaml.safe_load((ROOT / "configs" / "frozen.yaml").read_text())
OUT = LOG_DIR / os.environ.get("RESULTS_DIR", "results")


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = load_meta()
    pool = [m for m in meta.values() if m["kind"] == "benign" and m["split"] == "pool"]
    attacks = [m for m in meta.values() if m["kind"] == "attack" and m["split"] == "eval"]
    print(f"pool={len(pool)} attacks={len(attacks)} completed={sum(m['completed'] for m in attacks)}", flush=True)
    cal_all, ev_all = {}, []
    for fam in FAMILIES:
        for ovl in P["overlaps"]:
            cal_ids, ev_ids = draw_backgrounds(pool, fam, ovl, P["n_background"], P["seed"])
            st, hid = merge(cal_ids, seed=P["seed"])
            maps = build_maps(st, hid, await embeddings(st), M=P["M"], h=P["h"], tau_route=P["tau_route"])
            cal = await calibrate(st, hid, maps, sample=P["cal_sample"], seed=P["seed"])
            for m, rows in cal.items():
                cal_all[f"{fam}|{ovl}|{m}"] = rows
            print(f"[{fam} @ {ovl}] calibrated on {len(st)} requests; usage={llm.USAGE}", flush=True)
            for a in sorted((x for x in attacks if x["family"] == fam), key=lambda x: x["episode_id"]):
                if not a["completed"]:
                    continue
                st2, hid2 = merge(ev_ids, seed=P["seed"], attack=a["episode_id"])
                maps2 = build_maps(st2, hid2, await embeddings(st2), M=P["M"], h=P["h"], tau_route=P["tau_route"])
                res = await evaluate(st2, hid2, maps2, a["completing_request"], cap=P["eval_cap"], seed=P["seed"])
                for m, r in res.items():
                    ev_all.append({"family": fam, "overlap": ovl, "map": m, "task": f"{fam}-{a['k']}",
                                   "attack": a["attack"], "episode": a["episode_id"], "completed": True, **r})
            (OUT / "cal.json").write_text(json.dumps(cal_all))
            (OUT / "ev.json").write_text(json.dumps(ev_all))
            print(f"[{fam} @ {ovl}] evaluated; usage={llm.USAGE}", flush=True)
    excluded = [a["episode_id"] for a in attacks if not a["completed"]]
    (OUT / "excluded.json").write_text(json.dumps(excluded))
    print("done. excluded (failed even unmonitored):", len(excluded))

asyncio.run(main())
