"""Held-out validation must use unchanged calibration thresholds and strict ties."""
import importlib.util
from pathlib import Path

import pytest


def test_reference_rate_keeps_calibration_threshold_fixed():
    path = Path(__file__).resolve().parents[1] / "scripts/exploratory_v2_benign.py"
    spec = importlib.util.spec_from_file_location("v2_benign", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    row = module.rate_row([["c", 0], ["c", 1]], [["v", 0.5], ["v", 0.8], ["v", 0.9]], 0.5)
    assert row["threshold"] == 0.5 and row["flagged"] == 2 and row["requests"] == 3
    assert row["fraction"] == 2/3 and row["calibration_fraction"] == 0.5
    with pytest.raises(ValueError, match="empty held-out"):
        module.rate_row([["c", 0]], [], 0.02)
