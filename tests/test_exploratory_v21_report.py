"""Follow-up reporting rejects incomplete matrices and never publishes partial safety."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest


def test_report_intervals_reject_nonfinite_and_reversed_values():
    path = Path(__file__).resolve().parents[1] / 'scripts/exploratory_v21_report.py'
    spec = importlib.util.spec_from_file_location('v21_report_interval', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.interval({'estimate': -.1, 'ci': [-.2, 0]}) == '-10.00 [-20.00, 0.00]'
    with pytest.raises(ValueError):
        module.interval({'estimate': float('nan'), 'ci': [0, 1]})
    with pytest.raises(ValueError):
        module.interval({'estimate': 0, 'ci': [1, 0]})


def test_report_rejects_partial_duplicate_and_invalid_score_matrices():
    path = Path(__file__).resolve().parents[1] / 'scripts/exploratory_v21_report.py'
    spec = importlib.util.spec_from_file_location('v21_report_complete', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = {'config': {'families': ['f'], 'judged_maps': ['m'], 'insertions': 1,
                           'backgrounds': {'calibration': 1, 'evaluation': 1}},
                'attacks': [{'id': 'e', 'route': 'private'}]}
    case = {'episode': 'e', 'route': 'private', 'insertion': 0, 'completed': True,
            'scores': {'m': [{'score': 1, 'size': 1}] * 3}}
    scores = {'cases': [case], 'calibration': {'f': {'m': [['b', 0, 1]] * 9}},
              'reference': {'f': {'m': [['v', 0, 1]] * 9}}}
    module.verify_complete(manifest, scores)
    for bad in [[], [case, case]]:
        with pytest.raises(ValueError, match='incomplete or duplicate'):
            module.verify_complete(manifest, {**scores, 'cases': bad})
    bad = copy.deepcopy(scores)
    bad['reference']['f']['m'][0][1] = float('nan')
    with pytest.raises(ValueError, match='invalid benign'):
        module.verify_complete(manifest, bad)


def test_live_reports_partial_progress_without_partial_safety_claim(tmp_path):
    path = Path(__file__).resolve().parents[1] / 'scripts/exploratory_v21_live.py'
    spec = importlib.util.spec_from_file_location('v21_live_partial', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / 'exploratory_scores.json').write_text('{broken')
    (tmp_path / 'exploratory_replay_progress.json').write_text(json.dumps({'completed': 10, 'target': 432}))
    text = module.render(tmp_path)
    assert '10/432' in text and 'not final safety estimates' in text
    assert 'Original global calibration' in text
    (tmp_path / 'exploratory_temporal_wording_screen.json').write_text(json.dumps({
        'matches': 1, 'distinct_step_matches': [{'category': 'worlds', 'tool': 'read'}]}))
    assert '1 reused benign read descriptions' in module.render(tmp_path)


def test_live_completion_waits_for_planned_judged_supplement(tmp_path):
    path = Path(__file__).resolve().parents[1] / 'scripts/exploratory_v21_live.py'
    spec = importlib.util.spec_from_file_location('v21_live_completion', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert not module.reporting_complete(tmp_path)
    (tmp_path / 'exploratory_report_complete.json').write_text('{}')
    assert module.reporting_complete(tmp_path)
    (tmp_path / 'exploratory_identifier_evaluation_plan.json').write_text('{"supplement":true}')
    assert not module.reporting_complete(tmp_path)
    (tmp_path / 'exploratory_identifier_report_complete.json').write_text('{}')
    assert module.reporting_complete(tmp_path)


def test_live_flags_stopped_collector_instead_of_claiming_progress(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[1] / 'scripts/exploratory_v21_live.py'
    spec = importlib.util.spec_from_file_location('v21_live_transport', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / 'exploratory_transport_primary_status.json').write_text(json.dumps({'phase': 'Running', 'pid': 12345}))

    def missing(pid, signal):
        raise ProcessLookupError

    monkeypatch.setattr(module.os, 'kill', missing)
    assert 'Collector process stopped' in module.render(tmp_path)
