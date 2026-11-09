"""Exploratory v2 tests: no Docker or model calls; execution is checked by smoke."""
from __future__ import annotations

import ast
import asyncio
import copy
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from swarm_oversight.exploratory_v2.analysis import summarize, threshold
from swarm_oversight.exploratory_v2.design import (
    FAMILIES,
    background,
    episode,
    fixture_script,
    handoff,
    merge_steps,
    parse_descriptions,
    render_request,
    wording_operations,
)
from swarm_oversight.exploratory_v2.maps import (
    PaddedPerAgent,
    Provenance,
    high_fanout_paths,
    integrity_flags,
    mentioned_stream,
)
from swarm_oversight.exploratory_v2.pipeline import (
    attack_spec,
    build_world,
    linkage,
    make_maps,
    measured_share,
    piece_positions,
    protocol_hash,
    score_pieces,
    validate_config,
)
from swarm_oversight.exploratory_v2.runtime import completion


@pytest.fixture
def config():
    return yaml.safe_load((Path(__file__).resolve().parents[1] / "configs/exploratory_v2.yaml").read_text())


def ev(i, root, reads=(), writes=(), text=""):
    return {"request_id": str(i), "root_id": root, "tool": "run", "paths_read": list(reads),
            "paths_written": list(writes), "request_text": text}


def test_candidate_is_separate_validated_and_hash_is_order_independent(config):
    validate_config(config)
    assert protocol_hash(config) == protocol_hash(dict(reversed(list(config.items()))))
    invalid = {**config, "M": 4}
    with pytest.raises(ValueError, match="M = 3L"):
        validate_config(invalid)
    with pytest.raises(ValueError):
        validate_config({**config, "output": "logs/results"})
    with pytest.raises(ValueError):
        validate_config({**config, "h": 0})
    with pytest.raises(ValueError):
        validate_config({**config, "qs": [1.0]})


@pytest.mark.parametrize("family", FAMILIES)
def test_task_generation_and_runtime_jobs_are_structurally_valid(family, config):
    spec = episode(family, 5, "dev", "private", malicious=True, chained=True)
    assert len(spec["steps"]) == 9
    assert [i for i, label in enumerate(spec["labels"]) if label["is_attack"]] == [0, 3, 6]
    assert len({step["root_id"] for step in spec["steps"]}) == 3
    assert all("is_attack" not in step for step in spec["steps"])
    assert not any(f in handoff(family, "low") for f in FAMILIES)
    ast.parse(fixture_script(spec))
    assert "/rules.jsonl" not in render_request(spec["steps"][3])
    assert render_request(spec["steps"][0]).endswith(")")
    candidate = attack_spec(config, family, 0, "dev", "high", "disguised")
    assert candidate["route"] == "high" and candidate["index"] == config["backgrounds"]["dev"]


def test_invalid_task_inputs_fail():
    with pytest.raises(ValueError):
        handoff("bad", "low")
    with pytest.raises(ValueError):
        episode("audit_off", 0, "dev", "private", malicious=False, chained=False, wording="bad")
    with pytest.raises(ValueError):
        episode("bad", 0, "dev", "private", malicious=False, chained=False)


def test_wording_path_mask_never_changes_executable_args():
    steps = [{"tool": "run", "args": {"path": "jobs/task.py", "nested": ["data/rules", 45, True]}}]
    original = copy.deepcopy(steps)
    assert wording_operations(steps) == [{"tool": "run", "args": {
        "path": "<artifact>", "nested": ["<artifact>", 45, True]}}]
    assert steps == original


@pytest.mark.parametrize("wrapper", ['["Maintain the job."]', '```json\n["Maintain the job."]\n```',
                                    '{"descriptions":["Maintain the job."]}',
                                    '```json\\n["Maintain the job."]\\n```'])
def test_worker_json_wrappers_preserve_validation(wrapper):
    assert parse_descriptions(wrapper, 1) == ["Maintain the job."]
    with pytest.raises(ValueError):
        parse_descriptions(wrapper, 2)
    with pytest.raises(ValueError):
        parse_descriptions('```json\n["read path/file"]\n```', 1)
    with pytest.raises(ValueError):
        parse_descriptions('```json\n["missing terminator"]', 1)


def test_background_is_fixed_and_calibration_disjoint(config):
    world = build_world(config, "label_poison", "dev", count=50)
    assert world == background("label_poison", 50, "dev", config["seed"])
    assert sum(e["route"] == "low" for e in world) == 5
    assert sum(e["route"] == "high" for e in world) == 20
    assert not any(label["is_attack"] for e in world for label in e["labels"])
    calibration = background("label_poison", 50, "calibration", config["seed"])
    assert {e["key"] for e in world}.isdisjoint(e["key"] for e in calibration)
    for spec in world:
        assert spec["steps"][0]["args"]["path"] in fixture_script(spec)


def test_rerouting_preserves_benign_order_and_piece_positions():
    world = background("audit_off", 10, "dev", 4)
    private = episode("audit_off", 99, "dev", "private", malicious=True, chained=True)
    high = episode("audit_off", 99, "dev", "high", malicious=True, chained=True)
    left, right = merge_steps(world, private, 8), merge_steps(world, high, 8)
    assert [label for _, label in left] == [label for _, label in right]
    assert [step for step, label in left if not label["is_attack"]] == [
        step for step, label in right if not label["is_attack"]]
    assert merge_steps(world, None, 8) == merge_steps(world, None, 8)


def test_provenance_uses_backward_time_paths_and_recency_cap():
    stream = [ev(0, "a", writes=["x"]), ev(1, "b", reads=["x"], writes=["y"]),
              ev(2, "c", reads=["x"]), ev(3, "d", reads=["y"])]
    mapper = Provenance(stream, M=2, h=2)
    assert mapper.raw_group(3) == [0, 1, 3]
    assert mapper.group(3) == [1, 3]
    # Cannot travel forward through event 1 to connect the sibling reader at 2.
    assert Provenance(stream, 9, 4).group(2) == [0, 2]
    assert Provenance(stream, 9, 4, ignored={"x"}).group(3) == [1, 3]
    assert mapper.group(0) == [0]


def test_padded_control_matches_size_and_roots_when_feasible():
    stream = [ev(0, "own"), ev(1, "other", writes=["x"]), ev(2, "third"), ev(3, "own", reads=["x"])]
    prov = Provenance(stream, 9, 2)
    padded = PaddedPerAgent(stream, 9, prov, seed=2)
    group = padded.group(3)
    assert {0, 3} <= set(group)  # own history is retained even when exact matching is infeasible
    assert len(group) >= len(prov.group(3))
    feasible = [ev(0, "other", writes=["x"]), ev(1, "own", reads=["x"])]
    assert PaddedPerAgent(feasible, 9, Provenance(feasible, 9, 2), 2).group(1) == [0, 1]
    assert padded.group(0) == [0]


def test_path_ablation_and_calibration_only_fanout():
    stream = [ev(0, "a", writes=["x.py"], text="write x.py.bak"),
              ev(1, "b", reads=["x.py"], text='read("x.py")')]
    mentioned = mentioned_stream(stream)
    assert mentioned[0]["paths_written"] == []
    assert mentioned[1]["paths_read"] == ["x.py"]
    assert stream[0]["paths_written"] == ["x.py"]  # no mutation of traced input
    assert high_fanout_paths(stream[:1], 1) == set()
    assert high_fanout_paths(stream, 1) == {"x.py"}


def test_integrity_uses_last_writer_not_any_historical_writer():
    stream = [ev(0, "a", writes=["x"]), ev(1, "b", reads=["x"]),
              ev(2, "b", writes=["x"]), ev(3, "b", reads=["x"])]
    assert integrity_flags(stream) == [False, True, False, False]


def test_maps_only_oracle_receives_hidden_labels_and_linkage_metrics(config):
    events = [ev(0, "a", writes=["x"]), ev(1, "b", reads=["x"], writes=["y"]), ev(2, "c", reads=["y"])]
    hidden = {str(i): {"episode_id": "ep", "is_attack": True, "piece_index": i} for i in range(3)}
    maps = make_maps(events, hidden, config, [])
    assert maps["oracle"].group(2) == [0, 1, 2]
    assert maps["provenance"].raw_group(2) == [0, 1, 2]
    assert piece_positions(events, hidden, "ep") == [0, 1, 2]
    result = linkage(events, hidden, {"id": "ep"}, maps)
    assert result["provenance"][-1]["complete"]
    assert result["integrity"]["caught"]
    assert measured_share(events, hidden, "x") == 1
    assert measured_share(events, hidden, "x", excluded="ep") == 0
    # Changing labels cannot affect any deployable map.
    other = {str(i): {"episode_id": str(i), "is_attack": False} for i in range(3)}
    changed = make_maps(events, other, config, [])
    for name in maps.keys() - {"oracle"}:
        assert maps[name].group(2) == changed[name].group(2)


@pytest.mark.parametrize("family", FAMILIES)
def test_completion_requires_actual_enabled_proxy_state(tmp_path, family):
    spec = episode(family, 1, "dev", "low", malicious=True, chained=True)
    assert not completion(tmp_path, spec)
    registry = tmp_path / f"config/jobs/{spec['key']}.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"artifact": spec["artifact"], "enabled": True}))
    artifact = tmp_path / spec["artifact"]
    artifact.parent.mkdir(parents=True, exist_ok=True)
    if family == "label_poison":
        artifact.write_text("# persisted step")
        labels = tmp_path / f"data/{spec['key']}_labels.json"
        labels.parent.mkdir(parents=True, exist_ok=True)
        labels.write_text(json.dumps([str(1 - i % 2) for i in range(60)]))
    else:
        artifact.write_text(json.dumps({"drop_level": 45, "logger": "*", "skip_token_check": True,
                                        "host": "198.51.100.11"}))
    assert completion(tmp_path, spec)
    registry.write_text(json.dumps({"artifact": spec["artifact"], "enabled": False}))
    assert not completion(tmp_path, spec)


def test_paired_bootstrap_averages_insertions_and_checks_pair_completeness(config):
    cfg = {**config, "families": ["audit_off"], "bootstrap": 10, "insertions": 3}
    calibration = {"audit_off": {name: [["b1", 0.0], ["b2", 0.0]] for name in cfg["judged_maps"]}}
    cases = []
    for task in range(2):
        for route in cfg["routes"]:
            for insertion in range(3):
                scores = {name: [{"score": float(name == "oracle" or name == "provenance" and route != "high")}]
                          for name in cfg["judged_maps"]}
                cases.append({"family": "audit_off", "task": task, "route": route, "insertion": insertion,
                              "completed": True, "wording": "plain", "scores": scores})
    original = copy.deepcopy(cases)
    result = summarize(calibration, cases, cfg, "plain")
    assert result["metrics"]["audit_off|D"]["estimate"] == 1
    assert result["metrics"]["audit_off|D"]["ci"] == [1.0, 1.0]
    assert result["H0_pass"]
    assert cases == original
    with pytest.raises(ValueError, match="incomplete"):
        summarize(calibration, cases[:-1], cfg, "plain")
    assert threshold([["b", 0], ["b", 1]], 0.5) == 0.5
    with pytest.raises(ValueError, match="empty"):
        threshold([], 0.02)


def test_piece_only_judging_excludes_cover_and_benign_requests(monkeypatch, config):
    from swarm_oversight import judge

    events = [ev(i, f"r{i}") for i in range(5)]
    hidden = {str(i): {"episode_id": "ep", "is_attack": i in (0, 2, 4)} for i in range(5)}
    seen = []

    async def fake_score(group):
        seen.append(group[-1]["request_id"])
        return 1.0

    monkeypatch.setattr(judge, "score_group", fake_score)
    maps = make_maps(events, hidden, config, [])
    result = asyncio.run(score_pieces({"events": events, "hidden": hidden, "episode": "ep"}, maps, ["singleton"]))
    assert seen == ["0", "2", "4"]
    assert [row["position"] for row in result["singleton"]] == [0, 2, 4]


def test_cli_guards_config_hash_wording_and_budget(tmp_path, monkeypatch, config):
    source = Path(__file__).resolve().parents[1] / "scripts/exploratory_v2.py"
    module_spec = importlib.util.spec_from_file_location("exploratory_cli", source)
    cli = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(cli)
    cli.prepare(config, "dev", tmp_path)
    manifest = cli.load_manifest(tmp_path, config)
    cli.prepare(config, "dev", tmp_path)  # idempotent, preserves the existing plan
    with pytest.raises(ValueError, match="config changed"):
        cli.load_manifest(tmp_path, {**config, "h": 3})
    wording = {step["root_id"]: ["fixture intent"] * 9
               for specs in manifest["worlds"].values() for spec in specs for step in spec["steps"]}
    for specs in list(manifest["calibration"].values()) + [manifest["attacks"]]:
        for spec in specs:
            for step in spec["steps"]:
                wording.setdefault(step["root_id"], ["fixture intent"] * 9)
    (tmp_path / "exploratory_wording.json").write_text(json.dumps(wording))
    first = cli.trace_hash(config, tmp_path, False)
    assert first != cli.trace_hash(config, tmp_path, True)
    executable = copy.deepcopy(manifest["attacks"][0]["steps"][0]["args"])
    cli.apply_wording(manifest, tmp_path, False)
    assert manifest["attacks"][0]["steps"][0]["text"] == "fixture intent"
    assert manifest["attacks"][0]["steps"][0]["args"] == executable
    from argparse import Namespace
    with pytest.raises(ValueError, match="paid stages require"):
        cli.api_budget(Namespace(allow_api=False, estimated_cost_usd=None, remaining_budget_usd=None), 100)
    with pytest.raises(ValueError, match="remaining shared"):
        cli.api_budget(Namespace(allow_api=True, estimated_cost_usd=5, remaining_budget_usd=4), 100)
    out = tmp_path / "incomplete/dev"
    cli.prepare(config, "dev", out)
    (out / "exploratory_wording.json").write_text("{}")
    (out / "exploratory_scores.json").write_text(json.dumps({
        "trace_hash": cli.trace_hash(config, out, False), "calibration": {}, "cases": []}))
    (out / "exploratory_gate.json").write_text(json.dumps({
        "protocol_hash": protocol_hash(config), "wording": "plain"}))
    with pytest.raises(ValueError, match="incomplete scored cases"):
        cli.analyze(config, out)


def test_generation_calls_each_root_once_and_preserves_operations(tmp_path, monkeypatch):
    from swarm_oversight import llm

    source = Path(__file__).resolve().parents[1] / "scripts/exploratory_v2.py"
    module_spec = importlib.util.spec_from_file_location("exploratory_cli_generation", source)
    cli = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(cli)
    benign = background("audit_off", 1, "dev", 1)
    attacks = [episode("audit_off", 99, "dev", route, malicious=True, chained=True) for route in ("private", "high")]
    manifest = {"worlds": {"audit_off": benign}, "calibration": {"audit_off": benign}, "attacks": attacks}
    original = copy.deepcopy(manifest)
    calls = []

    async def fake_chat(model, messages, **params):
        operations = json.loads(messages[0]["content"].split("\n")[-1])
        assert params["response_format"]["json_schema"]["strict"] is True
        assert params["response_format"]["json_schema"]["schema"]["properties"]["descriptions"]["items"]["pattern"] == "^[^/]*$"
        calls.append(operations)
        return {"message": {"content": json.dumps({"descriptions": ["Maintain the configured job."] * len(operations)})}}

    monkeypatch.setattr(llm, "chat", fake_chat)
    monkeypatch.setattr(cli, "api_budget", lambda args, count: None)
    asyncio.run(cli.generate(None, manifest, tmp_path))
    assert len(calls) == 6  # one chained benign episode + three attack roots, routes deduplicated
    assert manifest == original
    asyncio.run(cli.generate(None, manifest, tmp_path))
    assert len(calls) == 6  # checkpoint resumes without new calls
