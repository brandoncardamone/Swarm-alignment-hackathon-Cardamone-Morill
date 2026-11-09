"""EXPLORATORY supplementary identifier linkage; no model calls or primary-file edits."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from swarm_oversight.exploratory_v21_identifier import VisibleIdentifier

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    args = parser.parse_args()
    run = args.run
    manifest = json.loads((run / 'exploratory_manifest.json').read_text())
    scores = json.loads((run / 'exploratory_scores.json').read_text())
    paths = [ROOT / 'src/swarm_oversight/exploratory_v21_identifier.py', Path(__file__).resolve(),
             ROOT / 'docs/V21_IDENTIFIER_ADDENDUM.md']
    plan = {'analysis': 'exploratory_v21', 'supplementary_judge_free_only': True,
            'recorded_utc': datetime.now(UTC).isoformat(), 'new_api_calls': 0,
            'attack_score_cases_when_recorded': len(scores.get('cases', [])),
            'source_hashes': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    plan_file = run / 'exploratory_identifier_addendum.json'
    if plan_file.exists():
        previous = json.loads(plan_file.read_text())
        if previous['source_hashes'] != plan['source_hashes']:
            raise ValueError('supplement source changed; preserve and version the addendum')
    else:
        plan_file.write_text(json.dumps(plan, indent=2) + '\n')
    by_route = defaultdict(list)
    for path in sorted((run / 'cases').glob('*/exploratory_metadata.json')):
        case = json.loads(path.read_text())
        events = json.loads((path.parent / 'exploratory_events.json').read_text())
        hidden = json.loads((path.parent / 'exploratory_hidden.json').read_text())
        pieces = [i for i, e in enumerate(events) if hidden[e['request_id']]['episode_id'] == case['episode']
                  and hidden[e['request_id']]['is_attack']]
        if len(pieces) != 3:
            raise ValueError('invalid piece annotations')
        mapper = VisibleIdentifier(events, manifest['config']['M'])
        group, raw = set(mapper.group(pieces[-1])), set(mapper.raw_group(pieces[-1]))
        by_route[case['route']].append({'complete': set(pieces) <= group, 'complete_uncapped': set(pieces) <= raw,
            'size': len(group), 'precision': len(group & set(pieces)) / len(group),
            'roots': len({events[i]['root_id'] for i in group})})
    total = len(manifest['attacks']) * manifest['config']['insertions']
    if sum(len(v) for v in by_route.values()) != total:
        raise ValueError('incomplete replay matrix')
    result = {'analysis': 'exploratory_v21', 'supplementary_exploratory': True, 'judge_free_only': True,
              'no_safety_or_audit_cost_claim': True, 'new_api_calls': 0, 'cases': total, 'routes': {}}
    for route, values in by_route.items():
        result['routes'][route] = {'cases': len(values), 'complete': sum(v['complete'] for v in values),
            'complete_uncapped': sum(v['complete_uncapped'] for v in values),
            'mean_size': sum(v['size'] for v in values) / len(values),
            'mean_precision': sum(v['precision'] for v in values) / len(values),
            'mean_roots': sum(v['roots'] for v in values) / len(values)}
    (run / 'exploratory_identifier_linkage.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
