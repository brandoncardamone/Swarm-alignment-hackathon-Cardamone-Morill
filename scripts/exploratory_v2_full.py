"""EXPLORATORY full judging with the proposal's H0-on-evaluation test order.

This additive execution amendment keeps the original dev gate and all requests,
maps, parameters and judge prompts intact. Dev selects wording; evaluation H0
controls whether evaluation H1 is interpreted. The amendment is recorded before
any evaluation scores, separately from the original frozen experiment.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import runpy
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
PRICES = {"openrouter/mistralai/mistral-small-3.2-24b-instruct": (0.000000075, 0.0000002)}


def write_json(path: Path, data: dict) -> None:
    temp = path.with_suffix(".tmp.json")
    temp.write_text(json.dumps(data, indent=2))
    temp.replace(path)


def validate_wording_gate(gate: dict, protocol: str) -> str:
    if gate["protocol_hash"] != protocol:
        raise ValueError("pilot protocol differs from evaluation protocol")
    expected = "disguised" if gate["designated_oracle_caught"] >= 2 else "plain"
    if gate["wording"] != expected:
        raise ValueError("wording selection differs from the recorded dev criterion")
    # H0_pass is retained, never rewritten. Full-sample H0 gates H1 in summarize().
    return expected


def request_upper_bound(model: str, messages: list[dict], max_tokens: int) -> float:
    prompt_price, completion_price = PRICES[model]
    # UTF-8 byte count bounds normal text tokenization; overhead covers chat formatting.
    text_bytes = len(json.dumps(messages, ensure_ascii=False).encode()) + 256
    # Shared client: four outer attempts, one SDK retry per attempt.
    return 8 * (text_bytes * prompt_price + max_tokens * completion_price)


class BudgetGuard:
    """Reserve conservative in-flight costs; reconcile against account usage every 5 s."""

    def __init__(self, run: Path, client: httpx.AsyncClient, key: str):
        self.run, self.client, self.key = run, client, key
        self.lock, self.slots = asyncio.Lock(), asyncio.Semaphore(24)
        self.account_usage, self.reserved, self.updated = 20.0, 0.0, 0.0
        self.account_cap = 0.0
        self.completed: list[tuple[float, float]] = []
        self.active: set[asyncio.Task] = set()

    async def refresh(self) -> None:
        started = time.monotonic()
        response = await self.client.get("https://openrouter.ai/api/v1/credits",
                                         headers={"Authorization": "Bearer " + self.key})
        response.raise_for_status()
        data = response.json()["data"]
        self.account_usage = float(data["total_usage"])
        self.account_cap = float(data["total_credits"])
        self.completed = [(when, cost) for when, cost in self.completed if when >= started]
        self.updated = time.monotonic()
        write_json(self.run / "exploratory_budget_status.json", {
            "analysis": "exploratory_v2", "authorized_cap_usd": self.account_cap,
            "account_usage_usd": self.account_usage, "checked_utc": datetime.now(UTC).isoformat(),
            "note": "User explicitly authorized use of all available account credits."})

    def wrap(self, original, llm):
        async def guarded(model, messages, *, cache_tag="", **params):
            cache_key = hashlib.sha256(json.dumps([model, messages, params, cache_tag],
                                                  sort_keys=True, default=str).encode()).hexdigest()
            if llm._get(cache_key) is not None:
                return await original(model, messages, cache_tag=cache_tag, **params)
            upper = request_upper_bound(model, messages, params["max_tokens"])
            task = asyncio.current_task()
            self.active.add(task)
            try:
                async with self.slots:
                    async with self.lock:
                        used = self.account_usage + self.reserved + sum(cost for _, cost in self.completed)
                        if time.monotonic() - self.updated > 5 or used + upper > self.account_cap - 0.05:
                            await self.refresh()
                        used = self.account_usage + self.reserved + sum(cost for _, cost in self.completed)
                        if used + upper > self.account_cap - 0.05:
                            raise RuntimeError("Account budget reserve reached; checkpoints preserved, no new paid calls")
                        self.reserved += upper
                    try:
                        return await original(model, messages, cache_tag=cache_tag, **params)
                    finally:
                        async with self.lock:
                            self.reserved -= upper
                            self.completed.append((time.monotonic(), upper))
            finally:
                self.active.discard(task)
        return guarded


def initialize(run: Path, namespace: dict) -> tuple[dict, dict, dict]:
    output = run / "evaluation"
    manifest_path = output / "exploratory_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    config = manifest["config"]
    if namespace["protocol_hash"](config) != manifest["protocol_hash"]:
        raise ValueError("manifest protocol hash mismatch")
    gate_path = run / "dev/exploratory_gate.json"
    gate = json.loads(gate_path.read_text())
    wording = validate_wording_gate(gate, manifest["protocol_hash"])
    amendment_path = run / "exploratory_evaluation_amendment.json"
    hashes = {"runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
              "wording_sha256": hashlib.sha256((output / "exploratory_wording.json").read_bytes()).hexdigest(),
              "dev_gate_sha256": hashlib.sha256(gate_path.read_bytes()).hexdigest()}
    if amendment_path.exists():
        previous = json.loads(amendment_path.read_text())
        if any(previous[key] != value for key, value in hashes.items()):
            raise ValueError("amendment inputs changed; preserve this run and record a new version")
    else:
        if (output / "exploratory_scores.json").exists():
            raise ValueError("cannot change decision order after evaluation scoring has started")
        write_json(amendment_path, {"analysis": "exploratory_v2", **hashes,
                   "recorded_utc": datetime.now(UTC).isoformat(), "protocol_hash": manifest["protocol_hash"],
                   "selected_wording": wording, "dev_H0_pass": gate["H0_pass"],
                   "evaluation_scores_existed": False,
                   "budget_policy": "Latest user authorization permits all available account credits; "
                                    "prior $20 project cap is superseded for this exploratory run.",
                   "reason": "The imported v2 proposal uses dev to select wording and tests H0 on the full "
                             "evaluation before H1. The initial CLI incorrectly required a positive dev H0 CI.",
                   "unchanged": "Task count, requests, wording, maps, caps, hops, seeds, budgets, prompts, bootstrap "
                                "and the full-sample H0-before-H1 decision rule are unchanged."})
    return config, manifest, gate


async def score(run: Path, config: dict, manifest: dict, gate: dict, namespace: dict, wait_for_replay: bool) -> None:
    from swarm_oversight import llm
    from swarm_oversight.config import api_key
    from swarm_oversight.judge import score_group

    output = run / "evaluation"
    signature = namespace["trace_hash"](config, output, False)
    case_paths = sorted((output / "cases").glob("*/exploratory_metadata.json"))
    expected = {(s["id"], s["route"], i) for s in manifest["attacks"] for i in range(config["insertions"])
                if s["wording"] == gate["wording"]}
    observed = {(r["episode"], r["route"], r["insertion"])
                for r in (json.loads(p.read_text()) for p in case_paths)}
    if observed - expected or observed != expected and not wait_for_replay:
        raise ValueError("finish all selected-arm replay cases before judging")
    for path in case_paths + list((output / "calibration").glob("*/exploratory_metadata.json")):
        metadata = json.loads(path.read_text())
        if metadata.get("trace_hash") != signature or metadata.get("text_source") != "worker":
            raise ValueError("trace/wording mismatch or fixture data; refusing to judge")
    file = output / "exploratory_scores.json"
    saved = json.loads(file.read_text()) if file.exists() else {
        "analysis": "exploratory_v2", "trace_hash": signature, "calibration": {}, "cases": []}
    if saved["trace_hash"] != signature:
        raise ValueError("stale scores")
    saved["execution_amendment"] = json.loads((run / "exploratory_evaluation_amendment.json").read_text())
    calibration_events = {}
    original_chat = llm.chat
    async with httpx.AsyncClient(timeout=20) as client:
        guard = BudgetGuard(run, client, api_key("openrouter"))
        await guard.refresh()
        llm.chat = guard.wrap(original_chat, llm)
        try:
            for family in config["families"]:
                folder = output / "calibration" / family
                if wait_for_replay:
                    while not (folder / "exploratory_metadata.json").exists():
                        await asyncio.sleep(5)
                metadata = json.loads((folder / "exploratory_metadata.json").read_text())
                if metadata.get("trace_hash") != signature or metadata.get("text_source") != "worker":
                    raise ValueError("calibration trace mismatch")
                events = json.loads((folder / "exploratory_events.json").read_text())
                hidden = json.loads((folder / "exploratory_hidden.json").read_text())
                calibration_events[family] = events
                maps = namespace["make_maps"](events, hidden, config, events)
                cal = saved["calibration"].setdefault(family, {})
                for name in config["judged_maps"]:
                    if name in cal:
                        continue
                    values = await asyncio.gather(*(score_group([events[j] for j in maps[name].group(i)])
                                                    for i in range(len(events))))
                    cal[name] = [[hidden[e["request_id"]]["episode_id"], value]
                                 for e, value in zip(events, values, strict=True)]
                    write_json(file, saved)
                    print(f"Calibrated {family}/{name}", flush=True)
            while True:
                case_paths = sorted((output / "cases").glob("*/exploratory_metadata.json"))
                observed = {(r["episode"], r["route"], r["insertion"])
                            for r in (json.loads(p.read_text()) for p in case_paths)}
                if observed == expected:
                    break
                if observed - expected or not wait_for_replay:
                    raise ValueError("incomplete or unexpected evaluation cases")
                await asyncio.sleep(5)
            previous = {(r["episode"], r["route"], r["insertion"]) for r in saved["cases"]}
            for path in case_paths:
                case = json.loads(path.read_text())
                if case.get("trace_hash") != signature or case.get("text_source") != "worker":
                    raise ValueError("case trace mismatch")
                if (case["episode"], case["route"], case["insertion"]) in previous:
                    continue
                events = json.loads((path.parent / "exploratory_events.json").read_text())
                hidden = json.loads((path.parent / "exploratory_hidden.json").read_text())
                maps = namespace["make_maps"](events, hidden, config, calibration_events[case["family"]])
                case["scores"] = await namespace["score_pieces"]({**case, "events": events, "hidden": hidden},
                                                                 maps, config["judged_maps"])
                saved["cases"].append(case)
                write_json(file, saved)
                print(f"Scored {len(saved['cases'])}/{len(case_paths)} evaluation cases", flush=True)
        finally:
            pending = list(guard.active)
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
            llm.chat = original_chat
            await guard.refresh()
    summary = namespace["summarize"](saved["calibration"], saved["cases"], config, gate["wording"])
    write_json(output / "exploratory_summary.json", summary)
    write_json(run / "exploratory_execution_status.json", {
        "analysis": "exploratory_v2", "phase": "Full evaluation complete; writing local report"})
    print("Full evaluation complete; H0 pass:", summary["H0_pass"], flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--initialize-only", action="store_true")
    parser.add_argument("--wait-for-replay", action="store_true")
    parser.add_argument("--allow-api", action="store_true")
    parser.add_argument("--estimated-cost-usd", type=float)
    parser.add_argument("--remaining-budget-usd", type=float)
    args = parser.parse_args()
    namespace = runpy.run_path(str(ROOT / "scripts/exploratory_v2.py"))
    config, manifest, gate = initialize(args.run, namespace)
    if args.initialize_only:
        print("Recorded pre-scoring amendment; dev wording and all request/scoring parameters preserved.")
        return
    if (not args.allow_api or args.estimated_cost_usd is None or args.remaining_budget_usd is None
            or not 0 < args.estimated_cost_usd <= args.remaining_budget_usd):
        raise ValueError("explicit API opt-in, positive cost estimate and sufficient remaining budget required")
    print(f"EXPLORATORY full evaluation: expected incremental cost ${args.estimated_cost_usd:.2f}; "
          "live account-balance guard enabled; user authorized all available credits.", flush=True)
    write_json(args.run / "exploratory_execution_status.json", {
        "analysis": "exploratory_v2", "phase": "Full evaluation judging (H0 tested on full sample before H1)"})
    asyncio.run(score(args.run, config, manifest, gate, namespace, args.wait_for_replay))


if __name__ == "__main__":
    main()
