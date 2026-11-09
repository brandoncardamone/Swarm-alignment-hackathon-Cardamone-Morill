"""EXPLORATORY held-out benign-only reference validation; never refits thresholds."""
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

from swarm_oversight.exploratory_v2.analysis import threshold
from swarm_oversight.exploratory_v2.design import merge_steps
from swarm_oversight.exploratory_v2.runtime import execute_stream

ROOT = Path(__file__).resolve().parents[1]


def rate_row(calibration: list[list], validation: list[list], q: float) -> dict:
    tau = threshold(calibration, q)
    if not validation:
        raise ValueError("empty held-out validation")
    flagged = sum(score > tau for _, score in validation)
    return {"nominal_q": q, "threshold": tau, "flagged": flagged, "requests": len(validation),
            "fraction": flagged / len(validation),
            "calibration_fraction": sum(score > tau for _, score in calibration) / len(calibration)}


async def evaluate(args: argparse.Namespace, namespace: dict, full: dict, manifest: dict) -> None:
    from swarm_oversight import llm
    from swarm_oversight.config import api_key
    from swarm_oversight.judge import score_group

    run, config = args.run, manifest["config"]
    output = run / "evaluation"
    folder = output / "benign_validation"
    folder.mkdir(exist_ok=True)
    namespace["apply_wording"](manifest, output, False)
    signature = namespace["trace_hash"](config, output, False)
    primary = json.loads((output / "exploratory_scores.json").read_text())
    score_file = folder / "exploratory_scores.json"
    saved = json.loads(score_file.read_text()) if score_file.exists() else {
        "analysis": "exploratory_v2", "trace_hash": signature, "scores": {}}
    if saved["trace_hash"] != signature:
        raise ValueError("validation wording/config changed")
    print(f"EXPLORATORY held-out reference validation: estimated ${args.estimated_cost_usd:.2f}; "
          "existing thresholds and primary results unchanged.", flush=True)
    original = llm.chat
    async with httpx.AsyncClient(timeout=20) as client:
        guard = full["BudgetGuard"](folder, client, api_key("openrouter"))
        await guard.refresh()
        llm.chat = guard.wrap(original, llm)
        try:
            for family in config["families"]:
                trace_dir = folder / family
                if not (trace_dir / "exploratory_metadata.json").exists():
                    world = manifest["worlds"][family]
                    trace = execute_stream(world, merge_steps(world, None, config["seed"]), config["runner_image"])
                    if trace["failures"] or any(trace["completed"].values()):
                        raise RuntimeError("benign reference replay failed or contains proxy harm")
                    namespace["save_trace"](trace_dir, {**trace, "text_source": "worker", "trace_hash": signature})
                metadata = json.loads((trace_dir / "exploratory_metadata.json").read_text())
                if metadata["trace_hash"] != signature:
                    raise ValueError("reference trace changed")
                events = json.loads((trace_dir / "exploratory_events.json").read_text())
                hidden = json.loads((trace_dir / "exploratory_hidden.json").read_text())
                calibration = json.loads((output / "calibration" / family / "exploratory_events.json").read_text())
                maps = namespace["make_maps"](events, hidden, config, calibration)
                scores = saved["scores"].setdefault(family, {})
                for name in config["judged_maps"]:
                    if name in scores:
                        continue
                    values = await asyncio.gather(*(score_group([events[j] for j in maps[name].group(i)])
                                                    for i in range(len(events))))
                    scores[name] = [[hidden[e["request_id"]]["episode_id"], value]
                                    for e, value in zip(events, values, strict=True)]
                    full["write_json"](score_file, saved)
                    print(f"Validated held-out {family}/{name}", flush=True)
        finally:
            pending = list(guard.active)
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
            llm.chat = original
            await guard.refresh()
    rows = []
    for family in config["families"]:
        for name in config["judged_maps"]:
            for q in config["qs"]:
                rows.append({"family": family, "map": name,
                             **rate_row(primary["calibration"][family][name], saved["scores"][family][name], q)})
    summary = {"analysis": "exploratory_v2", "diagnostic_only": True,
               "reference_interleaving_seed": config["seed"], "primary_results_unchanged": True,
               "scope": "Benign-only held-out world at one fixed reference interleaving; "
                        "not actual audit rates in attack-containing streams or a threshold refit.",
               "rows": rows, "usage": llm.USAGE}
    full["write_json"](folder / "exploratory_summary.json", summary)
    full["write_json"](run / "exploratory_budget_status.json",
                       json.loads((folder / "exploratory_budget_status.json").read_text()))
    print("Held-out benign-only reference validation complete.", flush=True)


def append_report(run: Path) -> None:
    output = run / "evaluation"
    manifest = json.loads((output / "exploratory_manifest.json").read_text())
    summary = json.loads((output / "benign_validation/exploratory_summary.json").read_text())
    q = manifest["config"]["primary_q"]
    rows = [r for r in summary["rows"] if r["nominal_q"] == q]
    lines = ["", "## Held-out benign-only reference validation", "",
             "This supplementary exploratory diagnostic uses the same held-out benign episodes at "
             "one fixed reference interleaving, without an inserted attack. Existing calibration "
             "thresholds are unchanged; primary results and hypothesis decisions are not refitted. "
             "It does not measure audit fractions in all attack-containing streams. Counts are "
             "request-level descriptives, not independent episode samples or inferential confidence intervals.", "",
             "| Family | Map | Nominal q | Achieved calibration fraction | Held-out reference flags/requests | Held-out fraction |",
             "|---|---|---|---|---|---|"]
    for row in rows:
        lines.append(f"| {row['family']} | {row['map']} | {q:.1%} | {row['calibration_fraction']:.3%} | "
                     f"{row['flagged']}/{row['requests']} | {row['fraction']:.3%} |")
    lines += ["", "If held-out rates differ from nominal q or between maps, safety comparisons should "
              "be described as using nominal calibration budgets, not proven equal realized audit costs. "
              "No evaluation-derived threshold adjustment was applied.", "",
              "Source: `evaluation/benign_validation/exploratory_summary.json` under the run directory. "
              "The supplementary plan and reference traces are preserved alongside the primary results."]
    report = ROOT / "report/exploratory_v2.md"
    text = report.read_text().split("\n## Held-out benign-only reference validation", 1)[0]
    temp = report.with_suffix(".tmp.md")
    temp.write_text(text + "\n".join(lines) + "\n")
    temp.replace(report)
    (run / "exploratory_execution_status.json").write_text(json.dumps({
        "analysis": "exploratory_v2", "phase": "Complete: primary evaluation, held-out validation and local report written"}, indent=2))
    print(f"Updated {report} with measured held-out benign audit fractions.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--allow-api", action="store_true")
    parser.add_argument("--estimated-cost-usd", type=float)
    parser.add_argument("--remaining-budget-usd", type=float)
    args = parser.parse_args()
    if (not args.allow_api or args.estimated_cost_usd is None or args.remaining_budget_usd is None
            or not 0 < args.estimated_cost_usd <= args.remaining_budget_usd):
        raise ValueError("explicit API opt-in and a positive estimate within remaining funds are required")
    namespace = runpy.run_path(str(ROOT / "scripts/exploratory_v2.py"))
    full = runpy.run_path(str(ROOT / "scripts/exploratory_v2_full.py"))
    output = args.run / "evaluation"
    manifest = json.loads((output / "exploratory_manifest.json").read_text())
    plan_path = output / "exploratory_benign_validation_plan.json"
    own_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if plan_path.exists():
        if json.loads(plan_path.read_text())["source_sha256"] != own_hash:
            raise ValueError("supplementary validation source changed; preserve and version its plan")
    else:
        full["write_json"](plan_path, {"analysis": "exploratory_v2", "supplementary_diagnostic": True,
            "recorded_utc": datetime.now(UTC).isoformat(), "source_sha256": own_hash,
            "protocol_hash": manifest["protocol_hash"], "reference_seed": manifest["config"]["seed"],
            "primary_thresholds_results_and_hypotheses_unchanged": True,
            "purpose": "Measure held-out benign-only reference audit fractions; no attack-inserted audit-cost claim."})
    if args.wait:
        while not (output / "exploratory_summary.json").exists():
            time.sleep(5)
    elif not (output / "exploratory_summary.json").exists():
        raise ValueError("finish primary scoring first, or use --wait")
    asyncio.run(evaluate(args, namespace, full, manifest))
    if args.wait:
        while "## Additional design audits" not in (ROOT / "report/exploratory_v2.md").read_text():
            time.sleep(5)
    append_report(args.run)


if __name__ == "__main__":
    main()
