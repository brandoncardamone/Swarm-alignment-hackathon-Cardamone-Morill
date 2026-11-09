"""EXPLORATORY v2.1 collection; isolated files, immutable sources and account guard."""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import runpy
import shutil
import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
import yaml

from swarm_oversight import llm
from swarm_oversight.config import api_key, models
from swarm_oversight.exploratory_v2.design import episode, handoff
from swarm_oversight.exploratory_v2.maps import Provenance
from swarm_oversight.exploratory_v2.pipeline import linkage, measured_share, piece_positions, save_trace
from swarm_oversight.exploratory_v2.runtime import execute_stream, security_probe
from swarm_oversight.exploratory_v21.analysis import rates, summarize
from swarm_oversight.exploratory_v21.design import make_maps, plan
from swarm_oversight.exploratory_v21.judge import prompt_for, score_group

ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp.json')
    temp.write_text(json.dumps(data, indent=2))
    temp.replace(path)


def source_hashes() -> dict:
    paths = [Path(__file__).resolve(), ROOT / 'configs/exploratory_v21.yaml', ROOT / 'configs/models.yaml',
             ROOT / 'src/swarm_oversight/judge.py', ROOT / 'src/swarm_oversight/llm.py',
             ROOT / 'src/swarm_oversight/config.py', ROOT / 'pyproject.toml', ROOT / 'uv.lock', ROOT / 'pytest.ini',
             ROOT / 'scripts/exploratory_v2.py', ROOT / 'scripts/exploratory_v2_full.py']
    paths.append(ROOT / 'docs/V21_PROTOCOL.md')
    for directory in ['src/swarm_oversight/exploratory_v21', 'src/swarm_oversight/exploratory_v2',
                      'src/swarm_oversight/maps', 'sandbox/v2']:
        paths += [p for p in (ROOT / directory).iterdir() if p.is_file() and p.suffix != '.pyc']
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}


def create_manifest(parent: dict, old_wording: dict, config: dict) -> tuple[dict, dict]:
    manifest = {key: copy.deepcopy(parent[key]) for key in ['worlds', 'calibration']}
    manifest.update({'analysis': 'exploratory_v21', 'config': config, 'attacks': []})
    needed = set()
    for split in ['worlds', 'calibration']:
        for world in manifest[split].values():
            for spec in world:
                positions: dict[str, int] = {}
                for step in spec['steps']:
                    root = step['root_id']
                    pos = positions.get(root, 0)
                    step['text'] = old_wording[root][pos]
                    positions[root] = pos + 1
                    needed.add(root)
    for family in config['families']:
        for task in range(config['tasks_per_family']):
            index = config['backgrounds']['evaluation'] + config['fresh_task_offset'] + task
            for route in config['routes']:
                manifest['attacks'].append(episode(family, index, 'evaluation', route,
                                                   malicious=True, chained=True, wording=config['wording']))
    previous_ids = {s['id'] for s in parent['attacks']}
    if previous_ids & {s['id'] for s in manifest['attacks']}:
        raise ValueError('fresh task variants overlap the prior evaluation')
    return manifest, {root: old_wording[root] for root in needed}


def prepare(config: dict) -> Path:
    hashes = source_hashes()
    protocol = hashlib.sha256(json.dumps({'config': config, 'sources': hashes}, sort_keys=True).encode()).hexdigest()
    run = ROOT / config['output'] / protocol[:12]
    run.mkdir(parents=True, exist_ok=True)
    manifest_path = run / 'exploratory_manifest.json'
    if manifest_path.exists():
        if json.loads(manifest_path.read_text())['protocol_hash'] != protocol:
            raise ValueError('existing manifest does not match protocol')
        return run
    parent = ROOT / config['parent_run'] / 'evaluation'
    manifest, wording = create_manifest(json.loads((parent / 'exploratory_manifest.json').read_text()),
                                        json.loads((parent / 'exploratory_wording.json').read_text()), config)
    manifest['protocol_hash'] = protocol
    manifest['recorded_utc'] = datetime.now(UTC).isoformat()
    manifest['hypothesis_order'] = 'full-sample H0, then 20pp private-gain prerequisite, then H1; both policies retained'
    manifest['primary_policy'] = config['primary_policy']
    manifest['fresh_variants_not_new_attack_mechanisms'] = True
    snapshot = run / 'exploratory_collection_source_snapshot'
    for name in hashes:
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    write_json(run / 'exploratory_source_manifest.json', {'analysis': 'exploratory_v21', 'files': hashes,
               'protocol_hash': protocol, 'recorded_utc': manifest['recorded_utc']})
    write_json(manifest_path, manifest)
    write_json(run / 'exploratory_wording.json', wording)
    write_json(run / 'exploratory_status.json', {'phase': 'Prepared; no new evaluation scores', 'analysis': 'exploratory_v21'})
    print(f'Prepared EXPLORATORY v2.1: {run}', flush=True)
    return run


def verify_sources(run: Path) -> None:
    saved = json.loads((run / 'exploratory_source_manifest.json').read_text())['files']
    changed = [name for name, value in saved.items()
               if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != value]
    if changed:
        raise ValueError('Collection source changed; preserve/version the run: ' + ', '.join(changed))


async def preflight(run: Path) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get('https://openrouter.ai/api/v1/credits',
                                    headers={'Authorization': 'Bearer ' + api_key('openrouter')})
        response.raise_for_status()
        credit = response.json()['data']
        response = await client.get('https://openrouter.ai/api/v1/models')
        response.raise_for_status()
        ids = {models()[name]['model'].removeprefix('openrouter/') for name in ['worker', 'judge']}
        prices = {'openrouter/' + row['id']: (float(row['pricing']['prompt']), float(row['pricing']['completion']))
                  for row in response.json()['data'] if row['id'] in ids}
        if len(prices) != 2:
            raise ValueError('configured models not available in the verified catalog')
    images = (await asyncio.to_thread(subprocess.check_output,
              ['docker', 'image', 'ls', '--no-trunc', '--format', '{{.Repository}}:{{.Tag}} {{.ID}}'],
              text=True)).splitlines()
    selected = [row for row in images if row.startswith(('swarm-runner:0.1 ', 'swarm-runner-v2:0.1 '))]
    if len(selected) != 2:
        raise RuntimeError('Docker runner images missing; use docs/V2_SETUP.md build commands')
    for row in selected:
        await asyncio.to_thread(subprocess.run, ['docker', 'image', 'inspect', row.split()[1]],
                                capture_output=True, check=True)
    info = {'analysis': 'exploratory_v21', 'checked_utc': datetime.now(UTC).isoformat(),
            'total_credits': float(credit['total_credits']), 'total_usage': float(credit['total_usage']),
            'remaining': float(credit['total_credits']) - float(credit['total_usage']), 'prices': prices,
            'images': selected}
    write_json(run / 'exploratory_preflight.json', info)
    return info


def trace(folder: Path, specs: list[dict], execution_plan: list[tuple[dict, dict]], config: dict) -> dict:
    result = execute_stream(specs, execution_plan, config['runner_image'])
    if result['failures']:
        raise RuntimeError('Docker tool failure; preserve the trace before diagnosing')
    save_trace(folder, {**result, 'analysis': 'exploratory_v21', 'text_source': 'worker'})
    return result


def replay(run: Path, manifest: dict, stop: threading.Event) -> None:
    config = manifest['config']
    target = len(manifest['attacks']) * config['insertions']
    for split in ['calibration', 'reference']:
        for family in config['families']:
            if stop.is_set():
                return
            folder = run / split / family
            if (folder / '.ready').exists():
                continue
            world = manifest['calibration' if split == 'calibration' else 'worlds'][family]
            result = trace(folder, world, plan(world, None, config['seed']), config)
            if any(result['completed'].values()):
                raise ValueError('benign-only replay produced a proxy harm')
            (folder / '.ready').touch()
    done = 0
    for spec in manifest['attacks']:
        family = spec['family']
        world = manifest['worlds'][family]
        calibration = json.loads((run / 'calibration' / family / 'exploratory_events.json').read_text())
        for insertion in range(config['insertions']):
            if stop.is_set():
                return
            folder = run / 'cases' / f"{spec['id']}-{spec['route']}-{insertion}"
            if not (folder / '.ready').exists():
                alone = execute_stream([spec], plan([], spec, config['seed']), config['runner_image'])
                if alone['failures'] or not alone['completed'][spec['id']]:
                    raise ValueError('standalone proxy task failed')
                result = execute_stream(world + [spec], plan(world, spec, config['seed'] + 1009*spec['index'] + insertion),
                                        config['runner_image'])
                if result['failures'] or not result['completed'][spec['id']]:
                    raise ValueError('merged proxy task failed; do not silently exclude it')
                maps = make_maps(result['events'], result['hidden'], config, calibration)
                links = linkage(result['events'], result['hidden'], spec, maps)
                if any(row['size'] != 2 for row in links['per_agent']):
                    raise ValueError('cover history missing at an attack piece')
                if not all(row['matched_size'] and row['matched_roots'] for row in links['size_root_matched']):
                    raise ValueError('exact matched control failed')
                case = {'analysis': 'exploratory_v21', 'family': family, 'task': spec['index'],
                        'route': spec['route'], 'insertion': insertion, 'episode': spec['id'], 'wording': 'plain',
                        'completed': True, 'rho': measured_share(result['events'], result['hidden'], handoff(family, spec['route']), spec['id']),
                        'linkage': links,
                        'hop_sweep': {str(h): linkage(result['events'], result['hidden'], spec,
                                      {'provenance': Provenance(result['events'], config['M'], h)})['provenance']
                                      for h in range(1, 5)}}
                save_trace(folder, {**case, 'events': result['events'], 'hidden': result['hidden'], 'text_source': 'worker'})
                (folder / '.ready').touch()
            done += 1
            write_json(run / 'exploratory_replay_progress.json', {'completed': done, 'target': target})
    print(f'All {target} cover-first replay cases complete.', flush=True)


async def wait_ready(folder: Path) -> None:
    while not (folder / '.ready').exists():
        await asyncio.sleep(1)


async def score_contexts(groups: list[list[dict]]) -> list[float]:
    # A single cached response for identical judge inputs, including simultaneous requests.
    unique = {prompt_for(group): group for group in groups}
    async with asyncio.TaskGroup() as task_group:
        jobs = {key: task_group.create_task(score_group(group)) for key, group in unique.items()}
    return [jobs[prompt_for(group)].result() for group in groups]


async def score_all(run: Path, manifest: dict) -> dict:
    config = manifest['config']
    target = len(manifest['attacks']) * config['insertions']
    batches = len(config['families']) * len(config['judged_maps'])
    file = run / 'exploratory_scores.json'
    saved = json.loads(file.read_text()) if file.exists() else {
        'analysis': 'exploratory_v21', 'calibration': {}, 'reference': {}, 'cases': [], 'control_audits': {}}
    calibration_events = {}
    for split in ['calibration', 'reference']:
        for family in config['families']:
            folder = run / split / family
            await wait_ready(folder)
            events = json.loads((folder / 'exploratory_events.json').read_text())
            hidden = json.loads((folder / 'exploratory_hidden.json').read_text())
            if split == 'calibration':
                calibration_events[family] = events
            maps = make_maps(events, hidden, config, calibration_events[family])
            data = saved[split].setdefault(family, {})
            for name in config['judged_maps']:
                if name in data:
                    continue
                indices = [maps[name].group(i) for i in range(len(events))]
                if name == 'size_root_matched':
                    matches = sum(len(group) == len(maps['provenance'].group(i)) and
                                  len({events[j]['root_id'] for j in group}) ==
                                  len({events[j]['root_id'] for j in maps['provenance'].group(i)})
                                  for i, group in enumerate(indices))
                    if matches != len(events):
                        raise ValueError('benign exact-control matching failed')
                    saved['control_audits'][f'{split}|{family}'] = {
                        'joint_matches': matches, 'requests': len(events),
                        'capacity_fallbacks': sum(maps[name].fallbacks.values())}
                values = await score_contexts([[events[j] for j in group] for group in indices])
                data[name] = [[hidden[event['request_id']]['episode_id'], value, len(group),
                               len({events[j]['root_id'] for j in group})]
                              for event, value, group in zip(events, values, indices, strict=True)]
                write_json(file, saved)
                write_json(run / 'exploratory_scoring_progress.json', {'phase': f'{split}: {family}/{name}',
                           'calibration_batches': sum(len(v) for v in saved['calibration'].values()),
                           'reference_batches': sum(len(v) for v in saved['reference'].values()),
                           'cases': len(saved['cases'])})
                print(f'Scored {split} {family}/{name}', flush=True)
    previous = {(c['episode'], c['route'], c['insertion']) for c in saved['cases']}
    for spec in manifest['attacks']:
        for insertion in range(config['insertions']):
            if (spec['id'], spec['route'], insertion) in previous:
                continue
            folder = run / 'cases' / f"{spec['id']}-{spec['route']}-{insertion}"
            await wait_ready(folder)
            case = json.loads((folder / 'exploratory_metadata.json').read_text())
            events = json.loads((folder / 'exploratory_events.json').read_text())
            hidden = json.loads((folder / 'exploratory_hidden.json').read_text())
            maps = make_maps(events, hidden, config, calibration_events[case['family']])
            pieces = piece_positions(events, hidden, case['episode'])
            if len(pieces) != 3:
                raise ValueError('expected exactly three attack pieces')
            requests, specifications = [], []
            for name in config['judged_maps']:
                for i in pieces:
                    group = maps[name].group(i)
                    requests.append([events[j] for j in group])
                    specifications.append((name, {'position': i, 'size': len(group),
                                                   'roots': len({events[j]['root_id'] for j in group})}))
            values = await score_contexts(requests)
            case['scores'] = {name: [] for name in config['judged_maps']}
            for (name, description), value in zip(specifications, values, strict=True):
                case['scores'][name].append({**description, 'score': value})
            saved['cases'].append(case)
            write_json(file, saved)
            write_json(run / 'exploratory_scoring_progress.json', {'phase': 'Attack-piece evaluation',
                       'calibration_batches': batches, 'reference_batches': batches, 'cases': len(saved['cases'])})
            print(f"Scored {len(saved['cases'])}/{target} evaluation cases", flush=True)
    return saved


async def collect(run: Path, args: argparse.Namespace) -> None:
    verify_sources(run)
    info = await preflight(run)
    if not args.allow_api or not 0 < args.estimated_cost_usd <= min(args.remaining_budget_usd, info['remaining']):
        raise ValueError('explicit API opt-in and estimate within verified remaining credits required')
    print(f"EXPLORATORY v2.1: estimated ${args.estimated_cost_usd:.2f}; available ${info['remaining']:.2f}; live account guard.", flush=True)
    manifest = json.loads((run / 'exploratory_manifest.json').read_text())
    config = manifest['config']
    old = runpy.run_path(str(ROOT / 'scripts/exploratory_v2.py'))
    budget = runpy.run_path(str(ROOT / 'scripts/exploratory_v2_full.py'))
    budget['PRICES'].update(info['prices'])  # in-memory price book only; original source is unchanged
    original = llm.chat
    async with httpx.AsyncClient(timeout=30) as client:
        guard = budget['BudgetGuard'](run, client, api_key('openrouter'))
        await guard.refresh()
        llm.chat = guard.wrap(original, llm)
        try:
            write_json(run / 'exploratory_status.json', {'phase': 'Generating fresh task descriptions'})
            await old['generate'](SimpleNamespace(allow_api=True, estimated_cost_usd=0.10,
                                                  remaining_budget_usd=min(20, info['remaining'])), manifest, run)
            old['apply_wording'](manifest, run, False)
            write_json(run / 'exploratory_effective_manifest.json', manifest)
            verify_sources(run)
            write_json(run / 'exploratory_status.json', {'phase': 'Docker replay and complete calibration/reference scoring'})
            stop = threading.Event()
            try:
                async with asyncio.TaskGroup() as tasks:
                    tasks.create_task(asyncio.to_thread(replay, run, manifest, stop))
                    scoring = tasks.create_task(score_all(run, manifest))
                saved = scoring.result()
            finally:
                stop.set()
        finally:
            active = list(guard.active)
            for task in active:
                task.cancel()
            if active:
                await asyncio.gather(*active, return_exceptions=True)
            llm.chat = original
            await guard.refresh()
    verify_sources(run)
    write_json(run / 'exploratory_status.json', {'phase': 'Paired bootstrap analysis; no further model calls'})
    summaries = {}
    for policy in config['policies']:
        summaries[policy] = summarize(saved['calibration'], saved['cases'], config, policy)
        print(f'Completed paired analysis: {policy}', flush=True)
    reference = []
    for policy in config['policies']:
        for family in config['families']:
            for name in config['judged_maps']:
                for q in config['qs']:
                    reference.append({'family': family, 'map': name,
                        **rates(saved['calibration'][family][name], saved['reference'][family][name],
                                q, policy, config['minimum_bin'])})
    write_json(run / 'exploratory_summary.json', {'analysis': 'exploratory_v21', 'policies': summaries,
               'primary_policy': config['primary_policy'], 'reference_rates': reference, 'client_usage': llm.USAGE})
    write_json(run / 'exploratory_status.json', {'phase': 'Complete: evaluation and analysis; local report ready to write'})
    print('Full v2.1 evaluation and both policy analyses complete.', flush=True)


def smoke(config: dict) -> None:
    security_probe(config['runner_image'])
    parent = json.loads((ROOT / config['parent_run'] / 'evaluation/exploratory_manifest.json').read_text())
    texts = json.loads((ROOT / config['parent_run'] / 'evaluation/exploratory_wording.json').read_text())
    manifest, _ = create_manifest(parent, texts, config)
    for family in config['families']:
        world = manifest['worlds'][family][:10]
        benign = execute_stream(world, plan(world, None, config['seed']), config['runner_image'])
        if benign['failures'] or any(benign['completed'].values()):
            raise ValueError('benign smoke failure')
        for route in config['routes']:
            spec = next(s for s in manifest['attacks'] if s['family'] == family and s['route'] == route)
            result = execute_stream(world + [spec], plan(world, spec, config['seed']), config['runner_image'])
            if result['failures'] or not result['completed'][spec['id']]:
                raise ValueError('cover-first smoke failure')
            maps = make_maps(result['events'], result['hidden'], config, benign['events'])
            links = linkage(result['events'], result['hidden'], spec, maps)
            assert all(row['size'] == 2 for row in links['per_agent'])
            assert all(row['matched_size'] and row['matched_roots'] for row in links['size_root_matched'])
            print(f'PASS cover-first {family}/{route}: completion, own history and exact matching', flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'smoke', 'run'])
    parser.add_argument('--config', type=Path, default=ROOT / 'configs/exploratory_v21.yaml')
    parser.add_argument('--allow-api', action='store_true')
    parser.add_argument('--estimated-cost-usd', type=float, default=0)
    parser.add_argument('--remaining-budget-usd', type=float, default=0)
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text())
    if config['analysis'] != 'exploratory_v21' or config['M'] != 9 or config['h'] != 2:
        raise ValueError('wrong follow-up configuration')
    if args.command == 'smoke':
        smoke(config)
        return
    run = prepare(config)
    if args.command == 'run':
        asyncio.run(collect(run, args))


if __name__ == '__main__':
    main()
