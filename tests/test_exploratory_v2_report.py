"""Final reporting must reject partial results and malformed numerical intervals."""
import importlib.util
from pathlib import Path

import pytest


def reporter():
    source = Path(__file__).resolve().parents[1] / "scripts/exploratory_v2_report.py"
    spec = importlib.util.spec_from_file_location("v2_report", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_intervals_keep_percentage_point_sign_and_reject_nan():
    module = reporter()
    assert module.interval({"estimate": -0.1, "ci": [-0.2, 0]}) == "-10.0 [-20.0, 0.0]"
    with pytest.raises(ValueError):
        module.interval({"estimate": float("nan"), "ci": [0, 1]})
    with pytest.raises(ValueError):
        module.interval({"estimate": 0.5, "ci": [0.8, 0.1]})


def test_reporting_rejects_missing_or_duplicate_case_pairs():
    module = reporter()
    manifest = {"config": {"insertions": 1, "families": ["f"], "judged_maps": ["m"]},
                "attacks": [{"id": "e", "route": "private", "wording": "plain"}]}
    case = {"episode": "e", "route": "private", "insertion": 0, "scores": {"m": [{"score": 1}] * 3}}
    summary = {"analysis": "exploratory_v2", "wording": "plain"}
    scores = {"cases": [case], "calibration": {"f": {"m": []}}}
    module.verify_complete(scores, summary, manifest, {"wording": "plain"})
    with pytest.raises(ValueError, match="incomplete or duplicate"):
        module.verify_complete({**scores, "cases": []}, summary, manifest, {"wording": "plain"})
    with pytest.raises(ValueError, match="incomplete or duplicate"):
        module.verify_complete({**scores, "cases": [case, case]}, summary, manifest, {"wording": "plain"})
