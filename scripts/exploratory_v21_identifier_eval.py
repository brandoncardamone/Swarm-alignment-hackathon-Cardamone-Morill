"""EXPLORATORY full judged identifier supplement; primary files stay unchanged."""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import runpy
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from swarm_oversight import llm
from swarm_oversight.config import api_key, models
from swarm_oversight.exploratory_v21.analysis import rates, summarize
from swarm_oversight.exploratory_v21_identifier import VisibleIdentifier

ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp.json')
    temp.write_text(json.dumps(value, indent=2))
    temp.replace(path)


def record_plan(run: Path) -> None:
    files = [Path(__file__).resolve(), ROOT / 'src/swarm_oversight/exploratory_v21_identifier.py',
             ROOT / 'src/swarm_oversight/exploratory_v21/judge.py',
             ROOT / 'src/swarm_oversight/exploratory_v21/analysis.py', ROOT / 'scripts/exploratory_v21.py',
             ROOT / 'docs/V21_IDENTIFIER_JUDGED_ADDENDUM.md', ROOT / 'configs/models.yaml']
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    path = run / 'exploratory_identifier_evaluation_plan.json'
    if path.exists():
        if json.loads(path.read_text())['source_hashes'] != hashes:
            raise ValueError('supplement source changed; preserve/version the plan')
        return
    scores = json.loads((run / 'exploratory_scores.json').read_text())
    write_json(path, {'analysis': 'exploratory_v21', 'supplementary_exploratory': True,
        'recorded_utc': datetime.now(UTC).isoformat(), 'source_hashes': hashes,
        'primary_scored_cases_when_recorded': len(scores['cases']),
        'primary_protocol_and_decisions_unchanged': True, 'models_wait_for_primary_summary': True,
        'estimated_additional_usd': 1.5})


async def evaluate(run: Path, args: argparse.Namespace) -> None:
    namespace = runpy.run_path(str(ROOT / 'scripts/exploratory_v21.py'))
    namespace['verify_sources'](run)
    folder = run / 'identifier_evaluation'
    folder.mkdir(exist_ok=True)
    primary = json.loads((run / 'exploratory_scores.json').read_text())
    primary_summary = json.loads((run / 'exploratory_summary.json').read_text())
    manifest = json.loads((run / 'exploratory_manifest.json').read_text())
    cfg = manifest['config']
    input_hashes = {name: hashlib.sha256((run / name).read_bytes()).hexdigest()
                    for name in ['exploratory_scores.json', 'exploratory_summary.json', 'exploratory_effective_manifest.json']}
    input_file = folder / 'exploratory_input_hashes.json'
    if input_file.exists() and json.loads(input_file.read_text()) != input_hashes:
        raise ValueError('primary inputs changed after supplement began')
    write_json(input_file, input_hashes)
    file = folder / 'exploratory_scores.json'
    saved = json.loads(file.read_text()) if file.exists() else {
        'analysis': 'exploratory_v21', 'supplementary_identifier': True,
        'calibration': {}, 'reference': {}, 'cases': []}
    budget = runpy.run_path(str(ROOT / 'scripts/exploratory_v2_full.py'))
    original = llm.chat
    async with httpx.AsyncClient(timeout=30) as client:
        guard = budget['BudgetGuard'](folder, client, api_key('openrouter'))
        await guard.refresh()
        if guard.account_cap - guard.account_usage < args.estimated_cost_usd:
            raise ValueError('supplement estimate exceeds available account credits')
        catalog = await client.get('https://openrouter.ai/api/v1/models')
        catalog.raise_for_status()
        model = models()['judge']['model']
        price = next(row['pricing'] for row in catalog.json()['data'] if 'openrouter/' + row['id'] == model)
        budget['PRICES'][model] = (float(price['prompt']), float(price['completion']))
        llm.chat = guard.wrap(original, llm)
        print(f'EXPLORATORY judged identifier supplement: estimated ${args.estimated_cost_usd:.2f}; account guard active.', flush=True)
        try:
            for split in ['calibration', 'reference']:
                for family in cfg['families']:
                    if family in saved[split]:
                        continue
                    trace = run / split / family
                    events = json.loads((trace / 'exploratory_events.json').read_text())
                    hidden = json.loads((trace / 'exploratory_hidden.json').read_text())
                    mapper = VisibleIdentifier(events, cfg['M'])
                    groups = [mapper.group(i) for i in range(len(events))]
                    values = await namespace['score_contexts']([[events[j] for j in group] for group in groups])
                    saved[split][family] = [[hidden[event['request_id']]['episode_id'], value, len(group),
                                             len({events[j]['root_id'] for j in group})]
                                            for event, value, group in zip(events, values, groups, strict=True)]
                    write_json(file, saved)
                    print(f'Identifier {split}: {family}', flush=True)
            previous = {(c['episode'], c['route'], c['insertion']) for c in saved['cases']}
            for case in primary['cases']:
                key = (case['episode'], case['route'], case['insertion'])
                if key in previous:
                    continue
                trace = run / 'cases' / f"{key[0]}-{key[1]}-{key[2]}"
                events = json.loads((trace / 'exploratory_events.json').read_text())
                mapper = VisibleIdentifier(events, cfg['M'])
                positions = [row['position'] for row in case['scores']['singleton']]
                groups = [mapper.group(i) for i in positions]
                values = await namespace['score_contexts']([[events[j] for j in group] for group in groups])
                saved['cases'].append({'episode': key[0], 'route': key[1], 'insertion': key[2],
                    'scores': [{'position': i, 'score': value, 'size': len(group)}
                               for i, value, group in zip(positions, values, groups, strict=True)]})
                write_json(file, saved)
                if len(saved['cases']) % 12 == 0:
                    print(f"Identifier cases: {len(saved['cases'])}/{len(primary['cases'])}", flush=True)
        finally:
            tasks = list(guard.active)
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            llm.chat = original
            await guard.refresh()
    merged = copy.deepcopy(primary)
    extended = copy.deepcopy(cfg)
    extended['judged_maps'] = [*cfg['judged_maps'], 'identifier']
    for split in ['calibration', 'reference']:
        for family in cfg['families']:
            merged[split][family]['identifier'] = saved[split][family]
    by_case = {(c['episode'], c['route'], c['insertion']): c['scores'] for c in saved['cases']}
    if len(by_case) != len(primary['cases']):
        raise ValueError('incomplete supplementary matrix')
    for case in merged['cases']:
        case['scores']['identifier'] = by_case[case['episode'], case['route'], case['insertion']]
    results = {}
    for policy in cfg['policies']:
        result = summarize(merged['calibration'], merged['cases'], extended, policy)
        for key, value in primary_summary['policies'][policy]['metrics'].items():
            if result['metrics'][key] != value:
                raise ValueError('primary metric changed in the extended paired analysis')
        results[policy] = result
    reference = [{'family': family, **rates(saved['calibration'][family], saved['reference'][family], q,
                                            policy, cfg['minimum_bin'])}
                 for family in cfg['families'] for policy in cfg['policies'] for q in cfg['qs']]
    write_json(folder / 'exploratory_summary.json', {'analysis': 'exploratory_v21', 'supplementary_identifier': True,
        'primary_metrics_reproduced_identically': True, 'policies': results, 'reference_rates': reference,
        'client_usage': llm.USAGE, 'primary_scores_sha256': input_hashes['exploratory_scores.json']})
    write_json(run / 'exploratory_budget_status.json', json.loads((folder / 'exploratory_budget_status.json').read_text()))
    print('Judged identifier supplement complete; primary estimates/CIs reproduced identically.', flush=True)


def append_report(run: Path) -> None:
    summary = json.loads((run / 'identifier_evaluation/exploratory_summary.json').read_text())
    cfg = json.loads((run / 'exploratory_manifest.json').read_text())['config']
    lines = ['', '## Supplementary exploratory judged identifier control', '',
             'This comparator was specified after the zero-cost linkage check and before any of its own model '
             'judgments. The primary five-map evaluation is unchanged. It uses the same fixed traces, public brief, '
             'judge, M=9, q values and paired-bootstrap method. It is not a new confirmatory hypothesis or a '
             'statistical superiority claim. All primary estimates and CIs reproduced identically when this sixth '
             'map was added in memory. Group selection uses visible arguments, while the judge retains the '
             'common logged-path inputs used by all maps; this is not a complete no-instrumentation monitor ablation.', '',
             '| Policy | Family | Private safety [95% CI]; caught/n | Low safety [95% CI]; caught/n | High safety [95% CI]; caught/n |',
             '|---|---|---|---|---|']
    for policy in cfg['policies']:
        result = summary['policies'][policy]
        for family in cfg['families']:
            cells = []
            for route in cfg['routes']:
                key = f'{family}|identifier|{route}'
                value, count = result['metrics'][key], result['counts'][key]
                cells.append(f"{100*value['estimate']:.2f}% [{100*value['ci'][0]:.2f}, {100*value['ci'][1]:.2f}]; "
                             f"{count['caught_insertions']}/{count['completed_insertions']}")
            lines.append(f'| {policy} | {family} | ' + ' | '.join(cells) + ' |')
    lines += ['', '| Policy | Family | Nominal q | Benign reference flags/n | Fraction |', '|---|---|---|---|---|']
    for row in summary['reference_rates']:
        if row['q'] == cfg['primary_q']:
            lines.append(f"| {row['policy']} | {row['family']} | {row['q']:.1%} | {row['flagged']}/{row['requests']} | "
                         f"{row['fraction']:.3%} |")
    lines += ['', '| Policy | Family | Size bin | Calibration n | Threshold | Global backoff | Reference flags/n |',
              '|---|---|---|---|---|---|---|']
    for row in summary['reference_rates']:
        if row['q'] == cfg['primary_q']:
            for b in row['bins']:
                label = ['1', '2–3', '4–9'][b['bin']]
                lines.append(f"| {row['policy']} | {row['family']} | {label} | {b['calibration_requests']} | "
                             f"{b['threshold']:.6f} | {b['global_fallback']} | {b['flagged']}/{b['requests']} |")
    budget = json.loads((run / 'identifier_evaluation/exploratory_budget_status.json').read_text())
    lines += ['', 'Do not infer superiority from overlapping/non-overlapping marginal CIs; no paired identifier-versus-'
              'provenance superiority test was specified. Identifier syntax is benchmark-specific. Realized audit rates '
              'may still differ across maps and policies; q is not a token/human-labor budget.', '',
              f"Supplement client counters: `{summary['client_usage']}`. Latest verified total account usage: "
              f"${budget['account_usage_usd']:.4f}, including earlier work, not an exact per-run bill.", '',
              'Source: identifier_evaluation/exploratory_summary.json under the run directory; the separate prospective '
              'plan and source/input hashes are retained alongside it. No primary scores or hypotheses were changed.']
    report = ROOT / 'report/exploratory_v21.md'
    text = report.read_text().split('\n## Supplementary exploratory judged identifier control', 1)[0]
    temp = report.with_suffix('.tmp.md')
    temp.write_text(text + '\n'.join(lines) + '\n')
    temp.replace(report)
    write_json(run / 'exploratory_identifier_report_complete.json', {'complete': True, 'report': str(report)})
    print(f'Appended judged identifier results to {report}', flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--wait', action='store_true')
    parser.add_argument('--allow-api', action='store_true')
    parser.add_argument('--estimated-cost-usd', type=float, default=0)
    args = parser.parse_args()
    if not args.allow_api or args.estimated_cost_usd <= 0:
        raise ValueError('API opt-in and positive announced estimate required')
    record_plan(args.run)
    if args.wait:
        while not (args.run / 'exploratory_summary.json').exists():
            time.sleep(5)
    asyncio.run(evaluate(args.run, args))
    if args.wait:
        while not (args.run / 'exploratory_report_complete.json').exists():
            time.sleep(5)
    append_report(args.run)


if __name__ == '__main__':
    main()
