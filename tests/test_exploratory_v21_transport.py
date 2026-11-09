"""Transport recovery must preserve cached calls and bound in-flight pressure."""
import asyncio
import importlib.util
from pathlib import Path


def test_transport_retries_only_transient_exception_groups():
    path = Path(__file__).resolve().parents[1] / 'scripts/exploratory_v21_transport.py'
    spec = importlib.util.spec_from_file_location('v21_transport_errors', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.transient(ExceptionGroup('network', [TimeoutError()]))
    assert not module.transient(ExceptionGroup('mixed', [TimeoutError(), ValueError()]))


def test_transport_limits_concurrency_and_preserves_model_arguments(monkeypatch):
    path = Path(__file__).resolve().parents[1] / 'scripts/exploratory_v21_transport.py'
    spec = importlib.util.spec_from_file_location('v21_transport_pressure', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.llm, '_get', lambda key: None)
    active, peak, calls = 0, 0, []

    async def original(model, messages, **params):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        calls.append((model, messages, params))
        await asyncio.sleep(.001)
        active -= 1
        return {'ok': True}

    async def exercise():
        wrapper = module.PacedChat(original, 2, 0)
        values = await asyncio.gather(*(wrapper('m', [{'content': str(i)}], max_tokens=3) for i in range(7)))
        assert all(v == {'ok': True} for v in values)
        monkeypatch.setattr(module.llm, '_get', lambda key: {'cached': True})
        assert await wrapper('m', [], cache_tag='tag', max_tokens=3) == {'ok': True}

    asyncio.run(exercise())
    assert peak <= 2 and len(calls) == 8
    assert calls[-1] == ('m', [], {'cache_tag': 'tag', 'max_tokens': 3})
