"""EXPLORATORY v2 live tracker. Reads local checkpoints; makes no API calls."""
from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from swarm_oversight.exploratory_v2.analysis import threshold

ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def render_live(run: Path, root: Path = ROOT) -> str:
    manifest = read_json(run / "evaluation/exploratory_manifest.json")
    dev_manifest = read_json(run / "dev/exploratory_manifest.json")
    config = manifest.get("config", dev_manifest.get("config", {}))
    gate = read_json(run / "dev/exploratory_gate.json")
    status = read_json(run / "exploratory_execution_status.json")
    budget = read_json(run / "exploratory_budget_status.json")
    reference_budget = read_json(run / "evaluation/benign_validation/exploratory_budget_status.json")
    if reference_budget.get("checked_utc", "") > budget.get("checked_utc", ""):
        budget = reference_budget
    if "account_usage_usd" in budget:
        status["account_usage_usd"] = budget["account_usage_usd"]
    amendment = read_json(run / "exploratory_evaluation_amendment.json")
    validation_plan = read_json(run / "evaluation/exploratory_benign_validation_plan.json")
    validation = read_json(run / "evaluation/benign_validation/exploratory_summary.json")
    primary_summary = read_json(run / "evaluation/exploratory_summary.json")
    if validation_plan and primary_summary and not validation:
        status["phase"] = "Primary evaluation complete; held-out benign-only reference validation in progress"
    lines = ["# Live results — exploratory v2", "",
             f"Updated {datetime.now(UTC).isoformat(timespec='seconds')}", "",
             f"Run: `{run.name}`. This tracker covers v2; the original frozen snapshot is preserved in "
             "[docs/RESULTS_FROZEN_SNAPSHOT.md](docs/RESULTS_FROZEN_SNAPSHOT.md).", "",
             f"**Phase:** {status.get('phase', 'Dev judging / evaluation preparation')}", "",
             "The latest user authorization permits all available account credits; "
             "a live usage/reservation guard is enabled."]
    if "account_usage_usd" in status:
        cap = budget.get("authorized_cap_usd")
        lines.append(f"Last verified account usage: ${status['account_usage_usd']:.4f}.")
        if cap is not None:
            lines.append(f"Available account balance: ${max(0, cap-status['account_usage_usd']):.4f} "
                         f"of ${cap:.2f} total credits.")
    for split in ("dev", "evaluation"):
        folder = run / split
        scores = read_json(folder / "exploratory_scores.json")
        wordings = read_json(folder / "exploratory_wording.json")
        paths = list((folder / "cases").glob("*/exploratory_metadata.json"))
        target = (len(config.get("families", [])) * config.get("dev_tasks_per_family", 0) *
                  len(config.get("wordings", [])) if split == "dev" else
                  len(config.get("families", [])) * config.get("tasks_per_family", 0))
        target *= len(config.get("routes", [])) * config.get("insertions", 0)
        maps = sum(len(v) for v in scores.get("calibration", {}).values())
        lines += ["", f"## {split.capitalize()}", "",
                  f"- Root descriptions checkpointed: {len(wordings)}.",
                  f"- Replay cases: {len(paths)}/{target} (evaluation target assumes one selected arm).",
                  f"- Calibration map batches: {maps}/15.",
                  f"- Scored cases checkpointed: {len(scores.get('cases', []))}."]
    lines += ["", "## Dev gate", ""]
    if gate:
        lines += [f"- Selected wording: **{gate['wording']}**.",
                  f"- H0 passed: **{gate['H0_pass']}**."]
        if not gate["H0_pass"] and amendment:
            lines.append("- Pilot H0 was inconclusive. A recorded pre-scoring amendment corrects the initial "
                         "CLI's overly strict pilot prerequisite: wording stays fixed, while the full evaluation "
                         "tests H0 before interpreting H1, as specified in the imported proposal.")
        elif not gate["H0_pass"]:
            lines.append("- The plan's linkage-only fallback applies. H1 safety is untested; "
                         "full-size replay is descriptive, not evidence of safety improvement.")
    else:
        lines.append("Pending. No full-evaluation safety claims yet.")
    if validation_plan:
        ref_scores = read_json(run / "evaluation/benign_validation/exploratory_scores.json")
        done = sum(len(v) for v in ref_scores.get("scores", {}).values())
        lines += ["", "## Supplementary held-out benign-only validation", "",
                  f"- Finished reference map batches: {done}/15.",
                  "- Uses unchanged calibration thresholds and a fixed benign-only reference interleaving.",
                  "- Does not refit primary results or measure audit rates in every attack-containing stream."]
        if validation:
            lines += ["", "| Family | Map | Nominal q | Reference flags/requests | Reference fraction |",
                      "|---|---|---|---|---|"]
            for row in validation["rows"]:
                if row["nominal_q"] == config["primary_q"]:
                    lines.append(f"| {row['family']} | {row['map']} | {row['nominal_q']:.1%} | "
                                 f"{row['flagged']}/{row['requests']} | {row['fraction']:.3%} |")
        elif done:
            calibration = read_json(run / "evaluation/exploratory_scores.json").get("calibration", {})
            lines += ["", "Reference rates for completed map batches only; the validation matrix is still incomplete.",
                      "Thresholds remain fixed. These are descriptive request fractions, not safety estimates.", "",
                      "| Family | Map | Nominal q | Reference flags/requests | Reference fraction |",
                      "|---|---|---|---|---|"]
            q = config.get("primary_q", 0.02)
            for family, maps in ref_scores["scores"].items():
                for name, rows in maps.items():
                    cal = calibration.get(family, {}).get(name)
                    if cal and rows:
                        tau = threshold(cal, q)
                        flags = sum(value > tau for _, value in rows)
                        lines.append(f"| {family} | {name} | {q:.1%} | {flags}/{len(rows)} | {flags/len(rows):.3%} |")
    lines += ["", "## Experimental design and runtime issues", ""]
    issue_file = root / "docs/EXPLORATORY_V2_DESIGN_ISSUES.md"
    if issue_file.exists():
        lines.extend(issue_file.read_text().splitlines()[2:])
    lines += ["", "## Observed evaluation diagnostics", ""]
    metas = [read_json(p) for p in (run / "evaluation/cases").glob("*/exploratory_metadata.json")]
    metas = [m for m in metas if m]
    if metas:
        completed = sum(bool(m.get("completed")) for m in metas)
        padded = [row for m in metas for row in m.get("linkage", {}).get("padded_per_agent", [])]
        mismatched = sum(not (r["matched_size"] and r["matched_roots"]) for r in padded)
        lines += [f"- Completed proxy goals: {completed}/{len(metas)} replay cases so far.",
                  f"- Padded-control size/root mismatches: {mismatched}/{len(padded)} piece groups."]
        for route in config.get("routes", []):
            values = [m["rho"] for m in metas if m.get("route") == route]
            if values:
                lines.append(f"- Measured benign hub share, {route}: {min(values):.1%}–{max(values):.1%}.")
    else:
        lines.append("No evaluation replay checkpoints yet.")
    control_audit = read_json(run / "exploratory_calibration_design_audit.json")
    if control_audit.get("calibration_padding"):
        lines += ["", "Calibration control audit (available families; no new judge calls):"]
        for family, data in control_audit["calibration_padding"].items():
            lines.append(f"- {family}: padded-control joint size/root matches "
                         f"{data['joint_matches']}/{data['requests']} benign request groups. "
                         "Attack-piece matching does not imply matched calibration contexts.")
    scored = read_json(run / "evaluation/exploratory_scores.json")
    if scored.get("calibration"):
        lines += ["", "Achieved calibration audit fractions (finished batches only; ties can under-use q):", "",
                  "| Family | Map | Nominal q | Fraction above threshold |", "|---|---|---|---|"]
        q = config.get("primary_q", 0.02)
        for family, maps in scored["calibration"].items():
            for name, rows in maps.items():
                if rows:
                    tau = threshold(rows, q)
                    rate = sum(value > tau for _, value in rows) / len(rows)
                    lines.append(f"| {family} | {name} | {q:.1%} | {rate:.3%} |")
        lines += ["", "These are calibration fractions; held-out benign judge audit rates are not measured "
                  "by the piece-only evaluation."]
    summary = read_json(run / "evaluation/exploratory_summary.json")
    lines += ["", "## Final results", ""]
    if summary:
        lines += [f"- H0 passed on evaluation: **{summary['H0_pass']}**.",
                  f"- Exploratory H1 decisions: `{summary['H1']}`."]
        effect = summary["metrics"]["overall|H0"]
        lines.append(f"- Oracle minus per-agent at private routing: {100*effect['estimate']:+.2f} pp "
                     f"[paired 95% CI {100*effect['ci'][0]:+.2f}, {100*effect['ci'][1]:+.2f}].")
        lines += ["", "Primary safety point estimates (paired CIs and raw counts are in the full report):", "",
                  "| Family | Provenance private | Provenance high | Per-agent private | Per-agent high |",
                  "|---|---|---|---|---|"]
        for family in config["families"]:
            values = [summary["metrics"][f"{family}|{name}|{route}"]["estimate"]
                      for name, route in [("provenance", "private"), ("provenance", "high"),
                                          ("per_agent", "private"), ("per_agent", "high")]]
            lines.append(f"| {family} | " + " | ".join(f"{v:.1%}" for v in values) + " |")
    else:
        lines.append("Pending. Partial checkpoints are progress indicators, not final safety estimates.")
    lines += ["", "Completed results are written locally to "
              "[report/exploratory_v2.md](report/exploratory_v2.md). No external upload is requested."]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--watch", type=int, default=0)
    args = parser.parse_args()
    while True:
        temp = ROOT / "RESULTS_LIVE.tmp.md"
        temp.write_text(render_live(args.run))
        temp.replace(ROOT / "RESULTS_LIVE.md")
        audit = args.run / "evaluation/exploratory_design_audit.json"
        report = ROOT / "report/exploratory_v2.md"
        final = audit.exists() and report.exists() and "## Additional design audits" in report.read_text()
        if (args.run / "evaluation/exploratory_benign_validation_plan.json").exists():
            final = final and (args.run / "evaluation/benign_validation/exploratory_summary.json").exists()
            final = final and "## Held-out benign-only reference validation" in report.read_text()
        if not args.watch or final:
            break
        time.sleep(args.watch)


if __name__ == "__main__":
    main()
