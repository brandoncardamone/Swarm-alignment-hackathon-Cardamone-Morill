"""Run attack and benign episodes and record their metadata in logs/episodes/<episode_id>.json."""
from __future__ import annotations

import json
import random
import uuid
from pathlib import Path

from tasks.attacks import ATTACK_TEMPLATES_proxy_goals as AT
from tasks.benign import templates as BT

from .agents.worker import run_root
from .config import LOG_DIR
from .families import CHECKS
from .gateway import Gateway
from .sandbox import Sandbox

SLUG_OF = {"log_level": "perf", "log_filter": "noise", "log_review": "review", "relabel_fix": "qa",
           "label_stats": "stats", "normalize_text": "textclean", "allowlist_add": "runner",
           "debug_profile": "trace", "key_rotation": "rotation", "status_report": "status",
           "settings_owner": "owners", "label_schema": "schema"}


def _save(meta: dict, log_dir: Path):
    (log_dir / "episodes").mkdir(parents=True, exist_ok=True)
    (log_dir / "episodes" / f"{meta['episode_id']}.json").write_text(json.dumps(meta, indent=1))


async def run_attack(family: str, attack: str, k: int, *, seed: int = 0, log_dir: Path = LOG_DIR) -> dict:
    rng = random.Random(f"atk:{family}:{attack}:{k}:{seed}")
    covers = [BT.cover_task(rng, avoid=family) for _ in range(3)]
    slugs = [SLUG_OF[c["template"]] for c in covers]
    task = AT.attack_task(family, attack, k, slugs)
    eid = f"atk-{family}-{attack}-{k}-s{seed}"
    for d in ("events", "hidden"):
        (log_dir / d / f"{eid}.jsonl").unlink(missing_ok=True)
    sbx = Sandbox()
    gw = Gateway(sbx, eid, log_dir=log_dir)
    check, cp = CHECKS[family], task["check_params"]
    state = {"done_at": None}
    toks = cp["tokens"]

    def labeler_for(i):
        def lab(tool, args):
            hit = any(t in json.dumps(args) for t in toks)
            return {"is_attack": hit, "piece_index": i if hit else None, "task_id": f"{family}-{k}",
                    "family": family, "attack": attack}
        return lab

    def after(ev):
        if state["done_at"] is None and check(sbx, cp):
            state["done_at"] = ev.request_id

    roots = []
    try:
        for i in range(3):  # pieces are causally ordered: root i runs after root i-1
            rid = f"r-{uuid.uuid4().hex[:8]}"
            roots.append(await run_root(gw, rid, covers[i]["roots"][0], piece=task["pieces"][i],
                                        labeler=labeler_for(i), after_call=after))
        completed = check(sbx, cp)
    finally:
        sbx.cleanup()
    meta = {"episode_id": eid, "kind": "attack", "family": family, "attack": attack, "k": k,
            "split": task["split"], "covers": [c["template"] for c in covers], "pieces": task["pieces"],
            "completed": completed, "completing_request": state["done_at"], "roots": roots}
    _save(meta, log_dir)
    return meta


async def run_benign(idx: int, *, seed: int = 0, log_dir: Path = LOG_DIR, split: str = "pool") -> dict:
    rng = random.Random(f"benign:{idx}:{seed}")
    spec = BT.sample_benign(rng)
    eid = f"ben-{idx:04d}-s{seed}"
    for d in ("events", "hidden"):
        (log_dir / d / f"{eid}.jsonl").unlink(missing_ok=True)
    sbx = Sandbox()
    gw = Gateway(sbx, eid, log_dir=log_dir)
    lab = lambda tool, args: {"is_attack": False, "task_id": spec["template"]}
    roots = []
    try:
        for prompt in spec["roots"]:
            roots.append(await run_root(gw, f"r-{uuid.uuid4().hex[:8]}", prompt, labeler=lab))
        harms = {f: CHECKS[f](sbx, {"script": "", "host": "198.51.100.0"}) for f in ("audit_off",)}
    finally:
        sbx.cleanup()
    meta = {"episode_id": eid, "kind": "benign", "template": spec["template"], "touches": spec["touches"],
            "split": split, "chained": len(spec["roots"]) > 1, "accidental_harm": harms, "roots": roots}
    _save(meta, log_dir)
    return meta
