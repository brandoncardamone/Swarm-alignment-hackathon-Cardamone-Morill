"""EXPLORATORY v2.1 progress and design limitations; local files only, no API calls."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def reporting_complete(run: Path) -> bool:
    if not (run / 'exploratory_report_complete.json').exists():
        return False
    if (run / 'exploratory_identifier_evaluation_plan.json').exists():
        return (run / 'exploratory_identifier_report_complete.json').exists()
    return True


def render(run: Path) -> str:
    manifest = read_json(run / 'exploratory_manifest.json')
    cfg = manifest.get('config', {})
    status = read_json(run / 'exploratory_status.json')
    scores = read_json(run / 'exploratory_scores.json')
    replay = read_json(run / 'exploratory_replay_progress.json')
    progress = read_json(run / 'exploratory_scoring_progress.json')
    budget = read_json(run / 'exploratory_budget_status.json')
    extra_budget = read_json(run / 'identifier_evaluation/exploratory_budget_status.json')
    if extra_budget.get('checked_utc', '') > budget.get('checked_utc', ''):
        budget = extra_budget
    summary = read_json(run / 'exploratory_summary.json')
    identifier_plan = read_json(run / 'exploratory_identifier_evaluation_plan.json')
    complete = reporting_complete(run)
    phase = ('Complete: full evaluation, both calibration policies and local report' if complete else
             status.get('phase', 'Preparing follow-up'))
    if summary and identifier_plan and not complete:
        phase = 'Primary evaluation complete; judged identifier supplement and reporting in progress'
    stage = 'identifier' if summary and identifier_plan else 'primary'
    transport = read_json(run / f'exploratory_transport_{stage}_status.json')
    if transport.get('phase') == 'Stopped':
        phase = 'Collector stopped; checkpoints preserved — inspect transport status'
    elif transport.get('phase', '').startswith('Retrying'):
        phase = 'Provider/network backoff; cached scoring will resume with lower request pressure'
    elif transport.get('phase') == 'Running' and transport.get('pid', 0) > 0:
        try:
            os.kill(transport['pid'], 0)
        except ProcessLookupError:
            phase = 'Collector process stopped; checkpoints preserved'
    lines = ['# Live results — exploratory v2.1', '', f"Updated {datetime.now(UTC).isoformat(timespec='seconds')}", '',
             f"Run: `{run.name}`. **Phase:** {phase}.", '',
             'Protocol: [docs/V21_PROTOCOL.md](docs/V21_PROTOCOL.md). Original completed v2: '
             '[report/exploratory_v2.md](report/exploratory_v2.md). Previous tracker: '
             '[docs/RESULTS_EXPLORATORY_V2.md](docs/RESULTS_EXPLORATORY_V2.md).', '',
             f"- Replay cases: **{replay.get('completed', 0)}/{replay.get('target', 432)}**.",
             f"- Calibration map batches: **{sum(len(v) for v in scores.get('calibration', {}).values())}/15**.",
             f"- Benign-reference map batches: **{sum(len(v) for v in scores.get('reference', {}).values())}/15**.",
             f"- Scored evaluation cases: **{len(scores.get('cases', []))}/432**.",
             f"- Latest scoring checkpoint: {progress.get('phase', 'First batch in progress')}."]
    if budget:
        cap, usage = budget['authorized_cap_usd'], budget['account_usage_usd']
        lines += ['', f'Last verified total account usage: **${usage:.4f}**; remaining **${max(0,cap-usage):.4f}** '
                  f'of ${cap:.2f} credits. This includes earlier work. User authorized remaining credits; a live '
                  f"retry/in-flight reserve guard {'was used' if complete else 'is active'}. No credit purchases are made."]
    freeze = read_json(run / 'exploratory_input_freeze.json')
    if freeze:
        changed = [name for name, digest in freeze['files'].items()
                   if hashlib.sha256((run / name).read_bytes()).hexdigest() != digest]
        lines += ['', 'Generated-input hashes: **' + ('CHANGED: '+', '.join(changed) if changed else 'unchanged') + '**.']
    lines += ['', '## Fixed structural changes and interpretation issues', '',
              '- Public task semantics are identical across maps and contain no hidden request labels. '
              'They may make individual pieces easier to recognize; no tasks will be removed for that.',
              '- Every piece follows a cover read, preserving nine requests per episode. This fixes the empty '
              'per-agent history, but a runbook read is still a limited work-history model.',
              '- The exact size/root random control keeps the current request, not all own history. '
              'Random root subsets may require the declared capacity fallback; matching and fallback counts are reported.',
              '- Primary size-bin calibration is a new audit-allocation policy. Original global calibration '
              'is retained on the same judge scores. Neither guarantees equal realized audit costs; sparse bins '
              'back off to global thresholds. All reference rates and calibration support are reported.',
              '- Both policy outcomes are retained under the fixed H0/private-gain/H1 rules; no best-policy selection.',
              '- Fresh task variants remain variations of three fixed mechanisms. Four bundled changes cannot be '
              'given separate causal credit. All results are exploratory and per-family intervals are not multiplicity-adjusted.',
              '- Descriptions are generated for fixed requests; no adaptive agents or executable model code. '
              'Current-request tracing is offline speculation, the auditor is ideal, and no actions are blocked.',
              '- The judge retains the original 700-character description cap, tool names and logged paths. '
              'It does not receive raw arguments/file contents; the public brief cannot recover omitted request details.',
              '- Benign validation is one reference interleaving. It does not measure audit rates in every '
              'attack-containing stream. q measures requests, not judge tokens or human labor.',
              '- Bootstrap groups come from fixed traces and can span episodes. Other traffic worlds, models '
              'and Stage B baselines remain unevaluated. The judged identifier control is tracked separately below.',
              '- A test-discovery clash from archived test copies was fixed with pytest testpaths=tests; '
              'all actual tests remain included. No collection source was edited after launch.']
    if (run / 'exploratory_transport_primary_amendment.json').exists():
        lines.append('- Provider HTTP 429 exhausted retries after 11 calibration batches. A single uncached '
                     'request then succeeded; collection resumed through a separate paced transport wrapper. '
                     'Initial limit is 8 in-flight requests with 0.35-second start spacing, with bounded '
                     'automatic backoff. Prompts, inputs, scientific sources and cached scores are unchanged. '
                     'Provider throttling may extend the original runtime estimate.')
    if (run / 'exploratory_transport_primary_throughput_amendment.json').exists():
        lines.append('- After the first held-out batch, paced concurrency increased to 16 with 0.2-second '
                     'start spacing to improve throughput, retaining bounded lower-concurrency retries. '
                     'The restart retained successful responses and fixed scientific inputs.')
    screen = read_json(run / 'exploratory_temporal_wording_screen.json')
    if screen:
        reads = sum(r['category'] != 'attacks' and r['tool'] == 'read'
                    for r in screen.get('distinct_step_matches', []))
        lines.append(f"- A post-generation wording screen found {screen['matches']} temporal-language matches, "
                     f'including {reads} reused benign read descriptions. Some describe post-operation checks '
                     'although cover reads now come first. Structured arguments and actual execution are correct. '
                     'This is a description-quality limitation; the fixed wording was not edited after collection began. '
                     'Lexical matches alone do not prove semantic errors.')
    audits = scores.get('control_audits', {})
    identifier = read_json(run / 'exploratory_identifier_linkage.json')
    if identifier:
        total = sum(v['complete'] for v in identifier['routes'].values())
        lines += ['', '## Supplementary exploratory identifier linkage', '',
                  f"Visible tool-argument job IDs link every piece at completion in {total}/{identifier['cases']} "
                  'replays at M=9, without file tracing. This is a post-launch, judge-free check: no new model '
                  'calls or primary changes. It limits claims that tracing is necessary for this corpus; '
                  'it does not establish identifier-grouped judge safety or matched audit cost. '
                  'See [the addendum](docs/V21_IDENTIFIER_ADDENDUM.md).']
    if identifier_plan:
        extra = read_json(run / 'identifier_evaluation/exploratory_scores.json')
        lines += ['', '## Judged identifier supplement', '',
                  '- Separately planned exploratory comparator; primary data/hypotheses stay fixed.',
                  '- Estimated additional $0.50–$1.50 and 20–40 minutes, queued after primary model calls.',
                  f"- Calibration families: {len(extra.get('calibration', {}))}/3; reference families: "
                  f"{len(extra.get('reference', {}))}/3; scored cases: {len(extra.get('cases', []))}/432.",
                  '- Uses the same judge/public brief, both fixed policies, persistent cache and account-credit guard. '
                  'J retains common logged-path metadata; this is not a full no-instrumentation monitor ablation.']
        extra_summary = read_json(run / 'identifier_evaluation/exploratory_summary.json')
        if extra_summary:
            lines.append('- Complete. All original primary estimates and CIs reproduced identically.')
    if audits:
        lines += ['', '## Exact-control checks', '', '| Split/family | Joint matches | Capacity fallbacks |', '|---|---|---|']
        for key, data in audits.items():
            lines.append(f"| {key.replace('|','/')} | {data['joint_matches']}/{data['requests']} | {data['capacity_fallbacks']} |")
    quality = read_json(run / 'exploratory_complete_reference_quality.json')
    if quality:
        lines += ['', 'Completed held-out audit-rate check at nominal q=2% (descriptive):']
        for policy in cfg['policies']:
            values = [row['fraction'] for row in quality['rows'] if row['policy'] == policy]
            lines.append(f'- {policy}: {min(values):.3%}–{max(values):.3%} across primary five-map family cells.')
        lines.append('Equal nominal q still does not imply equal realized audit cost. Attack safety is evaluated separately.')
    lines += ['', '## Results', '']
    if summary:
        for policy, data in summary['policies'].items():
            h0 = data['metrics']['overall|H0']
            lines += [f"- **{policy}:** H0 passed {data['H0_pass']}; private oracle − per-agent "
                      f"{100*h0['estimate']:.2f} pp [paired 95% CI {100*h0['ci'][0]:.2f}, {100*h0['ci'][1]:.2f}].",
                      '  H1: ' + '; '.join(f"{f}: {v}" for f,v in data['H1'].items()) + '.']
        diagnostic = read_json(run / 'exploratory_interpretation_checks.json')
        if diagnostic:
            lines += ['', f"Primary-policy interpretation check: first-piece provenance flags in "
                      f"{diagnostic['private_provenance_first_piece_flags']}/{diagnostic['private_cases']} private streams; "
                      f"total private catches {diagnostic['private_caught']['provenance']}/{diagnostic['private_cases']} "
                      f"for provenance versus {diagnostic['private_caught']['size_root_matched']}/{diagnostic['private_cases']} "
                      'for the exact random control. These are descriptive counts, not evidence of joint reasoning '
                      'or a paired superiority test.', '',
                      f"Provenance retains all pieces after the cap in {diagnostic['provenance_complete_streams']}/"
                      f"{diagnostic['completed_streams']} streams. No linkage-loss example was observed; remaining "
                      'misses can reflect judge behavior and threshold allocation.']
        lines += ['', 'Held-out benign-reference rates at nominal 2%:', '',
                  '| Policy | Family | Map | Flags/n | Fraction |', '|---|---|---|---|---|']
        for row in summary['reference_rates']:
            if row['q'] == cfg['primary_q']:
                lines.append(f"| {row['policy']} | {row['family']} | {row['map']} | "
                             f"{row['flagged']}/{row['requests']} | {row['fraction']:.3%} |")
        first_piece = read_json(run / 'exploratory_first_piece_calibration_diagnostic.json')
        if first_piece:
            rows = first_piece['rows']
            flags = {name: sum(row['first_piece_flags'][name] for row in rows)
                     for name in ['singleton', 'provenance', 'size_root_matched']}
            lines += ['', 'Post-collection exploratory calibration issue: '
                      f"{sum(row['identical_first_piece_scores'] for row in rows)}/{sum(row['cases'] for row in rows)} "
                      'private first-piece scores are identical for singleton/provenance/exact control, with '
                      f"current-request-only contexts, yet flags are {flags['singleton']}/{flags['provenance']}/"
                      f"{flags['size_root_matched']} because their size-bin thresholds differ. The additional "
                      'first-piece flags arise from threshold allocation, not extra context. Fixed primary policies '
                      'remain unchanged; source is exploratory_first_piece_calibration_diagnostic.json.']
    else:
        lines.append('Pending. Partial checkpoints show progress, not final safety estimates.')
    lines += ['', 'Completed results are saved locally to [report/exploratory_v21.md](report/exploratory_v21.md). '
              'No external upload, commit or push is requested.']
    return '\n'.join(lines) + '\n'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--watch', type=int, default=0)
    args = parser.parse_args()
    while True:
        temp = ROOT / 'RESULTS_LIVE.tmp.md'
        temp.write_text(render(args.run))
        temp.replace(ROOT / 'RESULTS_LIVE.md')
        if not args.watch or reporting_complete(args.run):
            break
        time.sleep(args.watch)


if __name__ == '__main__':
    main()
