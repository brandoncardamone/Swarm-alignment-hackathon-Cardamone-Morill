"""Live reporting must expose design limitations and distinguish partial results."""
import importlib.util
import json
from pathlib import Path


def test_live_tracker_partial_checkpoints_and_failed_gate(tmp_path):
    source = Path(__file__).resolve().parents[1] / "scripts/exploratory_v2_live.py"
    spec = importlib.util.spec_from_file_location("v2_live", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    run = tmp_path / "run"
    (run / "dev").mkdir(parents=True)
    (run / "dev/exploratory_manifest.json").write_text(json.dumps({"config": {
        "families": ["audit_off"], "dev_tasks_per_family": 2, "tasks_per_family": 16,
        "wordings": ["plain", "disguised"], "routes": ["private", "low", "high"], "insertions": 3}}))
    (run / "dev/exploratory_scores.json").write_text('{"incomplete":')
    text = module.render_live(run, tmp_path)
    assert "Pending. No full-evaluation safety claims yet." in text
    assert "not final safety estimates" in text
    (run / "dev/exploratory_gate.json").write_text(json.dumps({"wording": "plain", "H0_pass": False}))
    text = module.render_live(run, tmp_path)
    assert "linkage-only fallback" in text
    assert "No external upload" in text
    assert module.read_json(tmp_path / "missing.json") == {}
    (run / "exploratory_budget_status.json").write_text(json.dumps({
        "checked_utc": "2026-11-08T08:00:00Z", "account_usage_usd": 5, "authorized_cap_usd": 30}))
    reference = run / "evaluation/benign_validation"
    reference.mkdir(parents=True)
    (reference / "exploratory_budget_status.json").write_text(json.dumps({
        "checked_utc": "2026-11-08T08:01:00Z", "account_usage_usd": 5.5, "authorized_cap_usd": 30}))
    text = module.render_live(run, tmp_path)
    assert "account usage: $5.5000" in text and "balance: $24.5000" in text


def test_live_shows_completed_reference_batches_without_claiming_complete_validation(tmp_path):
    source = Path(__file__).resolve().parents[1] / "scripts/exploratory_v2_live.py"
    spec = importlib.util.spec_from_file_location("v2_live_reference", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    run = tmp_path / "run"
    reference = run / "evaluation/benign_validation"
    reference.mkdir(parents=True)
    (run / "evaluation/exploratory_manifest.json").write_text(json.dumps({"config": {
        "families": ["f"], "primary_q": 0.02}}))
    (run / "evaluation/exploratory_scores.json").write_text(json.dumps({"calibration": {
        "f": {"provenance": [["c", 0], ["c", 1]]}}}))
    (run / "evaluation/exploratory_benign_validation_plan.json").write_text('{"diagnostic": true}')
    (reference / "exploratory_scores.json").write_text(json.dumps({"scores": {
        "f": {"provenance": [["v", 0.5], ["v", 2]]}}}))
    text = module.render_live(run, tmp_path)
    assert "validation matrix is still incomplete" in text
    assert "| f | provenance | 2.0% | 1/2 | 50.000% |" in text
