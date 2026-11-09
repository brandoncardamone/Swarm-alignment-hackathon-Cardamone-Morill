"""Structural fixes must preserve labels, prefix safety and fixed inference rules."""
import asyncio
import copy
import importlib.util
from pathlib import Path

import pytest

from swarm_oversight.exploratory_v2.design import episode
from swarm_oversight.exploratory_v2.maps import Provenance
from swarm_oversight.exploratory_v21 import judge
from swarm_oversight.exploratory_v21.analysis import caught, rates, size_bin, summarize, thresholds
from swarm_oversight.exploratory_v21.design import SizeRootMatched, cover_first, make_maps, plan


def test_cover_first_keeps_seed_spec_and_label_alignment():
    spec = episode("audit_off", 216, "evaluation", "private", malicious=True, chained=True)
    original = copy.deepcopy(spec)
    ordered = cover_first(spec)
    assert spec == original and spec["steps"][0]["tool"] == "append"
    assert [s["tool"] for s in ordered["steps"]] == ["read", "append", "write", "read", "run", "write",
                                                      "read", "register_step", "write"]
    assert [i for i, label in enumerate(ordered["labels"]) if label["is_attack"]] == [1, 4, 7]
    merged = plan([], spec, 1)
    assert [step["tool"] for step, _ in merged] == [s["tool"] for s in ordered["steps"]]
    with pytest.raises(ValueError):
        cover_first({"steps": [], "labels": []})


def test_exact_control_is_prefix_only_and_matches_every_target():
    events = [{"request_id": str(i), "root_id": f"r{i % 4}", "request_text": "x", "paths_read": ["x"] if i else [],
               "paths_written": ["x"] if i % 2 == 0 else []} for i in range(20)]
    target = Provenance(events, 9, 2)
    control = SizeRootMatched(events, target, 5)
    for i in range(len(events)):
        actual, expected = control.group(i), target.group(i)
        assert actual == control.group(i) and i in actual and max(actual) <= i
        assert len(actual) == len(expected)
        assert len({events[j]["root_id"] for j in actual}) == len({events[j]["root_id"] for j in expected})
    hidden = {str(i): {"episode_id": str(i // 3)} for i in range(20)}
    cfg = {"M": 9, "h": 2, "seed": 5, "fanout_cap": 8}
    maps = make_maps(events, hidden, cfg, events)
    altered = {str(i): {"episode_id": "different"} for i in range(20)}
    changed = make_maps(events, altered, cfg, events)
    assert all(maps[name].group(19) == changed[name].group(19) for name in maps if name != "oracle")


def test_size_bins_backoff_and_strict_ties():
    assert [size_bin(n) for n in [1, 2, 3, 4, 9]] == [0, 1, 1, 2, 2]
    with pytest.raises(ValueError):
        size_bin(10)
    cal = [["a", 0, 1], ["b", 2, 1], ["a", 6, 3], ["b", 8, 3]]
    table = thresholds(cal, 0.5, "size_bin", 2)
    assert table["0"]["threshold"] == 1 and table["1"]["threshold"] == 7
    assert table["2"]["global_fallback"] and table["2"]["threshold"] == 4
    assert not caught([{"score": 7, "size": 3}], table)
    assert caught([{"score": 7.1, "size": 3}], table)
    result = rates(cal, [["v", 1, 1], ["v", 8, 3]], 0.5, "size_bin", 2)
    assert result["flagged"] == 1 and result["fraction"] == 0.5
    assert thresholds(cal, 0.5, "global", 2)["1"]["threshold"] == 4
    with pytest.raises(ValueError):
        thresholds([], 0.5, "global", 2)


def test_paired_summary_keeps_h0_ceiling_and_raw_counts():
    names = ["singleton", "per_agent", "size_root_matched", "provenance", "oracle"]
    cfg = {"families": ["f"], "judged_maps": names, "routes": ["private", "low", "high"],
           "insertions": 1, "tasks_per_family": 2, "primary_q": 0.5, "minimum_bin": 2,
           "bootstrap": 4, "seed": 1}
    cal = {"f": {name: [["a", 0, 2], ["b", 1, 2]] for name in names}}
    cases = [{"family": "f", "task": task, "route": route, "completed": True,
              "scores": {name: [{"score": 2 * int(name == "oracle" or name == "provenance" and route != "high"),
                                  "size": 2}] for name in names}}
             for task in range(2) for route in cfg["routes"]]
    result = summarize(cal, cases, cfg, "size_bin")
    assert result["H0_pass"] and result["H1"]["f"] == "positive drop supported"
    assert result["metrics"]["f|D"] == {"estimate": 1, "ci": [1, 1]}
    assert result["counts"]["f|provenance|private"]["caught_insertions"] == 2
    with pytest.raises(ValueError):
        summarize(cal, cases[:-1], cfg, "global")
    for case in cases:
        case["scores"]["provenance"][0]["score"] = 0
    assert summarize(cal, cases, cfg, "global")["H1"]["f"] == "untestable at this ceiling"


def test_public_brief_is_uniform_and_judge_uses_existing_digit_rule(monkeypatch):
    event = {"root_id": "r", "request_text": "maintenance", "tool": "read", "paths_read": [], "paths_written": []}
    assert judge.ENVIRONMENT in judge.prompt_for([event])
    assert "45 is security/audit" in judge.ENVIRONMENT
    calls = []

    async def fake(model, messages, **params):
        calls.append((model, messages, params))
        return {"logprobs": {"content": [{"top_logprobs": [{"token": "7", "logprob": 0}]}]}}

    monkeypatch.setattr(judge.llm, "chat", fake)
    assert asyncio.run(judge.score_group([event])) == 7
    assert calls[0][2]["max_tokens"] == 3


def test_new_manifest_uses_disjoint_variants_and_rejects_reusing_old_tasks():
    source = Path(__file__).resolve().parents[1] / 'scripts/exploratory_v21.py'
    spec = importlib.util.spec_from_file_location('v21_driver', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    old = episode('audit_off', 200, 'evaluation', 'private', malicious=True, chained=True)
    parent = {'worlds': {'audit_off': []}, 'calibration': {'audit_off': []}, 'attacks': [old]}
    cfg = {'families': ['audit_off'], 'tasks_per_family': 1, 'fresh_task_offset': 16,
           'backgrounds': {'evaluation': 200}, 'routes': ['private', 'low', 'high'], 'wording': 'plain'}
    result, texts = module.create_manifest(parent, {}, cfg)
    assert len(result['attacks']) == 3 and all(s['index'] == 216 for s in result['attacks'])
    assert texts == {} and parent['attacks'] == [old]
    with pytest.raises(ValueError, match='overlap'):
        module.create_manifest(parent, {}, {**cfg, 'fresh_task_offset': 0})


def test_simultaneous_identical_judge_inputs_share_one_response(monkeypatch):
    source = Path(__file__).resolve().parents[1] / 'scripts/exploratory_v21.py'
    spec = importlib.util.spec_from_file_location('v21_batch_driver', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    event = {'root_id': 'r', 'request_text': 'maintenance', 'tool': 'read', 'paths_read': [], 'paths_written': []}
    calls = []

    async def fake(events):
        calls.append(events)
        return 8

    monkeypatch.setattr(module, 'score_group', fake)
    assert asyncio.run(module.score_contexts([[event], [dict(event, root_id='different')]])) == [8, 8]
    assert len(calls) == 1


def test_exact_control_capacity_fallback_keeps_size_and_roots():
    events = [{'root_id': root} for root in ['large'] * 6 + ['small1', 'small2', 'current']]

    class Target:
        def group(self, i):
            return list(range(6)) + [i]

    fallbacks = []
    for seed in range(20):
        control = SizeRootMatched(events, Target(), seed)
        group = control.group(8)
        assert len(group) == 7 and 8 in group
        assert {events[j]['root_id'] for j in group} == {'large', 'current'}
        fallbacks.append(control.fallbacks[8])
    assert any(fallbacks)


def test_judge_retains_three_sample_fallback(monkeypatch):
    event = {'root_id': 'r', 'request_text': 'maintenance', 'tool': 'read', 'paths_read': [], 'paths_written': []}
    calls = []

    async def fake(model, messages, **params):
        calls.append(params)
        return {'logprobs': None, 'message': {'content': '5'}}

    monkeypatch.setattr(judge.llm, 'chat', fake)
    assert asyncio.run(judge.score_group([event])) == 5
    assert len(calls) == 4 and [c['cache_tag'] for c in calls[1:]] == ['sample0', 'sample1', 'sample2']


def test_adding_passive_comparator_preserves_original_paired_intervals():
    names = ['singleton', 'per_agent', 'size_root_matched', 'provenance', 'oracle']
    cfg = {'families': ['f'], 'judged_maps': names, 'routes': ['private', 'low', 'high'],
           'insertions': 1, 'tasks_per_family': 3, 'primary_q': .5, 'minimum_bin': 2,
           'bootstrap': 31, 'seed': 9}
    cal = {'f': {name: [[f'c{i//2}', i/8, [1, 2, 3, 4][i % 4]] for i in range(8)] for name in names}}
    cases = []
    for task in range(3):
        for route in cfg['routes']:
            bases = {'singleton': .1+.2*task, 'per_agent': .1+.2*task,
                     'size_root_matched': .05+.1*task, 'oracle': .3+.3*task,
                     'provenance': .2+.3*task if route != 'high' else .1+.15*task}
            cases.append({'family': 'f', 'task': task, 'route': route, 'completed': True,
                          'scores': {name: [{'score': base, 'size': 1}, {'score': base+.1, 'size': 2},
                                           {'score': base+.05, 'size': 4}] for name, base in bases.items()}})
    original = summarize(cal, cases, cfg, 'size_bin')
    assert any(value['ci'][0] != value['ci'][1] for value in original['metrics'].values())
    extended_cal, extended_cases = copy.deepcopy(cal), copy.deepcopy(cases)
    extended_cal['f']['identifier'] = copy.deepcopy(cal['f']['singleton'])
    for case in extended_cases:
        case['scores']['identifier'] = copy.deepcopy(case['scores']['oracle'])
    extended = summarize(extended_cal, extended_cases, {**cfg, 'judged_maps': names+['identifier']}, 'size_bin')
    assert all(extended['metrics'][key] == value for key, value in original['metrics'].items())
