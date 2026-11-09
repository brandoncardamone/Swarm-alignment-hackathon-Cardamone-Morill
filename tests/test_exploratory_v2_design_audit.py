"""Calibration matching can fail even when attack-piece matching is feasible."""
import copy
import importlib.util
from pathlib import Path

import pytest


def test_calibration_padding_reports_infeasible_own_history():
    source = Path(__file__).resolve().parents[1] / "scripts/exploratory_v2_design_audit.py"
    spec = importlib.util.spec_from_file_location("v2_design_audit", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    events = [{"root_id": "a", "paths_read": [], "paths_written": ["x"]},
              {"root_id": "a", "paths_read": [], "paths_written": []},
              {"root_id": "b", "paths_read": ["x"], "paths_written": []}]
    result = module.padding_audit(events, {"M": 9, "h": 2, "seed": 1})
    assert result == {"requests": 3, "size_matches": 2, "root_matches": 3, "joint_matches": 2}


def test_catches_distinguish_joint_context_and_partition_misses():
    source = Path(__file__).resolve().parents[1] / "scripts/exploratory_v2_design_audit.py"
    spec = importlib.util.spec_from_file_location("v2_context_audit", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    case = {"scores": {"m": [{"position": 0, "score": 1}, {"position": 3, "score": 9},
                              {"position": 6, "score": 8}]},
            "linkage": {"m": [{"position": i, "precision": k/9, "size": 9,
                                "complete": False, "complete_uncapped": True}
                               for i, k in [(0, 1), (3, 1), (6, 2)]]}}
    result = module.catch_context(case, "m", 7)
    assert result["caught"] and result["multi_piece"] and not result["earliest"]
    changed = copy.deepcopy(case)
    changed["scores"]["m"][-1]["score"] = 6
    assert not module.catch_context(changed, "m", 7)["multi_piece"]
    miss = module.catch_context(case, "m", 10)
    assert miss["map_miss"] and miss["cap_miss"] and not miss["judge_miss"]
    changed["linkage"]["m"][-1]["complete"] = True
    assert module.catch_context(changed, "m", 10)["judge_miss"]
    changed["linkage"]["m"][-1]["position"] = 5
    with pytest.raises(ValueError, match="position mismatch"):
        module.catch_context(changed, "m", 10)


def test_budget_equivalent_respects_strict_ties_and_censoring():
    source = Path(__file__).resolve().parents[1] / "scripts/exploratory_v2_design_audit.py"
    spec = importlib.util.spec_from_file_location("v2_budget_equivalent", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cal = [["b", score] for score in [0, 1, 2, 3]]
    value = module.budget_equivalent(cal, [0.5, 1.5, 2.5], 2, 1.0)
    assert 0.5 <= value < 0.500001
    assert module.budget_equivalent(cal, [0.5, 1.5, 2.5], 2, 0.4) is None
    assert module.budget_equivalent(cal, [0.5], 0, 0.1) == 0
    assert module.budget_equivalent([["b", 0]], [0], 1, 1) is None


def test_conditional_reference_rates_keep_global_threshold_and_strict_ties():
    source = Path(__file__).resolve().parents[1] / "scripts/exploratory_v2_design_audit.py"
    spec = importlib.util.spec_from_file_location("v2_conditional_rates", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    specs = [{"id": "a", "route": "high"}, {"id": "b", "route": "own"}]
    rows = module.conditional_rates([["cal", 0], ["cal", 1]],
                                    [["a", 0.5], ["a", 0.9], ["b", 0.8]], specs, 0.5)
    assert rows == [{"route": "high", "requests": 2, "flagged": 1, "fraction": 0.5, "threshold": 0.5},
                    {"route": "own", "requests": 1, "flagged": 1, "fraction": 1.0, "threshold": 0.5}]
    with pytest.raises(KeyError):
        module.conditional_rates([["cal", 0]], [["unknown", 1]], specs, 0.02)
