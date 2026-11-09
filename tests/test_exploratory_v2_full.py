"""The proposal tests H0 on evaluation, not as a positive-CI pilot prerequisite."""
import asyncio
import importlib.util
import time
from pathlib import Path
from types import SimpleNamespace

import pytest


def full_module():
    path = Path(__file__).resolve().parents[1] / "scripts/exploratory_v2_full.py"
    spec = importlib.util.spec_from_file_location("v2_full", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_inconclusive_pilot_preserves_wording_and_allows_full_h0_test():
    module = full_module()
    gate = {"protocol_hash": "same", "H0_pass": False, "designated_oracle_caught": 1, "wording": "plain"}
    assert module.validate_wording_gate(gate, "same") == "plain"
    assert gate["H0_pass"] is False
    with pytest.raises(ValueError, match="protocol differs"):
        module.validate_wording_gate(gate, "different")
    with pytest.raises(ValueError, match="wording selection"):
        module.validate_wording_gate({**gate, "wording": "disguised"}, "same")


def test_budget_reservation_includes_retry_and_output_envelopes():
    module = full_module()
    model = next(iter(module.PRICES))
    small = module.request_upper_bound(model, [{"role": "user", "content": "hello"}], 3)
    large = module.request_upper_bound(model, [{"role": "user", "content": "hello" * 50}], 3)
    assert 0 < small < large
    assert module.request_upper_bound(model, [{"role": "user", "content": "hello"}], 100) > small
    with pytest.raises(KeyError):
        module.request_upper_bound("unpriced/model", [], 3)


def test_guard_stops_new_paid_calls_and_allows_cached_responses(tmp_path):
    module = full_module()
    called = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": {"total_usage": 19.99, "total_credits": 20}}

    class Client:
        async def get(self, *args, **kwargs):
            return Response()

    async def original(*args, **kwargs):
        called.append(True)
        return {"cached": True}

    async def exercise():
        guard = module.BudgetGuard(tmp_path, Client(), "test-placeholder")
        guard.account_usage, guard.updated = 19.99, time.monotonic()
        blocked = guard.wrap(original, SimpleNamespace(_get=lambda key: None))
        with pytest.raises(RuntimeError, match="budget reserve"):
            await blocked(next(iter(module.PRICES)), [{"role": "user", "content": "hello"}], max_tokens=3)
        assert called == []
        assert guard.reserved == 0 and not guard.active
        cached = guard.wrap(original, SimpleNamespace(_get=lambda key: {"cached": True}))
        assert await cached("unpriced-but-cached", [], max_tokens=3) == {"cached": True}
        assert len(called) == 1
        class FundedResponse(Response):
            def json(self):
                return {"data": {"total_usage": 20.1, "total_credits": 30}}

        class FundedClient(Client):
            async def get(self, *args, **kwargs):
                return FundedResponse()

        funded = module.BudgetGuard(tmp_path, FundedClient(), "test-placeholder")
        allowed = funded.wrap(original, SimpleNamespace(_get=lambda key: None))
        await allowed(next(iter(module.PRICES)), [{"role": "user", "content": "hello"}], max_tokens=3)
        assert funded.account_cap == 30 and len(called) == 2
        assert funded.reserved == 0 and not funded.active

    asyncio.run(exercise())
