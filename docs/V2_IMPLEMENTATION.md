# Exploratory v2 implementation and evaluation checkpoint

Branch: `exploratory/v2-hub-routing`. No commit or push was made. The user requested the full evaluation
and local Markdown results, then explicitly authorized all available account credits. No external upload
is required. All 432 primary cases and all 15 supplementary benign-only validation batches are complete.

The active result is [`../report/exploratory_v2.md`](../report/exploratory_v2.md), with progress and runtime
issues in [`../RESULTS_LIVE.md`](../RESULTS_LIVE.md). The original frozen report remains separate.

## Files changed by this task

| File | Purpose |
|---|---|
| `PROJECT.md` | New exploratory v2 design, hypotheses, assumptions and status |
| `README.md` | Link the active branch design and setup guide |
| `docs/PROJECT_FROZEN.md` | Exact archive of the original PROJECT |
| `docs/V2_SETUP.md` | Local setup, offline checks, paid phases and deferred work |
| `docs/V2_IMPLEMENTATION.md` | This checkpoint and audit |
| `configs/exploratory_v2.yaml` | Separate candidate parameters; never replaces frozen.yaml |
| `src/swarm_oversight/exploratory_v2/__init__.py` | Separate namespace |
| `src/swarm_oversight/exploratory_v2/design.py` | Scripted plans, keyed append hand-offs and paired interleaving |
| `src/swarm_oversight/exploratory_v2/maps.py` | Prefix provenance, padded control, path ablation, fanout and integrity rule |
| `src/swarm_oversight/exploratory_v2/runtime.py` | One no-network Docker batch per speculative stream; state completion checks |
| `src/swarm_oversight/exploratory_v2/pipeline.py` | Piece-only scoring, linkage, hop sweep and separated trace artifacts |
| `src/swarm_oversight/exploratory_v2/analysis.py` | Paired task/calibration bootstrap, raw insertion counts, H0/H1 |
| `scripts/exploratory_v2.py` | Preflight/plan/prepare/smoke/generate/replay/judge/analyze CLI |
| `sandbox/v2/runner.Dockerfile` | Separate image based on the unchanged frozen runner |
| `sandbox/v2/entry.sh` | Batch timeout and startup error propagation |
| `sandbox/v2/hook_run.py` | Subprocess rejection and absolute result metadata path |
| `sandbox/v2/execute.py` | In-container execution, pre-call logging and effect tracing |
| `sandbox/v2/probe.py` | DNS/process isolation and cwd regression probe |
| `tests/test_exploratory_v2.py` | Offline tests including label invariance and mocked paid-client boundaries |
| `report/exploratory_v2.md` | Complete primary report, paired intervals and design limitations |
| `scripts/exploratory_v2_full.py` | Additive pre-scoring gate correction and live account-credit guard |
| `scripts/exploratory_v2_live.py` | V2 progress, audit fractions and design-issue tracker |
| `scripts/exploratory_v2_report.py` | Complete-matrix validation, local results report, scientific figure and CSVs |
| `scripts/exploratory_v2_design_audit.py` | Calibration matching, context catches, miss decomposition and hop audits |
| `tests/test_exploratory_v2_full.py` | Gate placement and account-budget boundary tests |
| `tests/test_exploratory_v2_live.py` | Honest partial/final status handling |
| `tests/test_exploratory_v2_report.py` | Reject partial/duplicate result matrices and invalid intervals |
| `tests/test_exploratory_v2_design_audit.py` | Calibration mismatch and cross-piece-context diagnostics |
| `docs/EXPLORATORY_V2_DESIGN_ISSUES.md` | Explicit observed/design limitations included in live and final results |
| `docs/RESULTS_FROZEN_SNAPSHOT.md` | Preserve original frozen live tracker before replacing its display |
| `RESULTS_LIVE.md` | Current exploratory v2 progress and design issues |

| `scripts/exploratory_v2_benign.py` | Supplementary held-out benign reference rates with fixed thresholds |
| `tests/test_exploratory_v2_benign.py` | Fixed-threshold and strict-tie validation tests |
| `analysis/exploratory_v2/` | Primary/descriptive q-sweep CSVs and post-result diagnostic JSON |
| `report/figures/exploratory_v2_*` | Scientific PNG/PDF figure |

Pre-existing/concurrent changes to `.gitignore`, `.agents/`, `v2.md` and `agents/worker.py` were left untouched.
The new artifacts under `logs/` and the SQLite cache remain gitignored. No credentials were printed.

## Setup and verification

- Installed locked dev extras with `uv sync --extra dev --locked`; Python 3.12.12 and uv 0.10.4.
- Built the missing original image and separate `swarm-runner-v2:0.1` image. Docker is running and the
  OpenRouter key is available locally. No further user setup is needed for this run.
- `uv run pytest -q`: **43 passed**, including the original tests; no model calls.
- Scoped Ruff over v2 modules, scripts, tests and sandbox: **passed**. `git diff --check`: **passed**.
- Original sandbox smoke: **9/9 passed**, repeated after primary scoring.
- V2 smoke: **9/9 family/route combinations passed**, including standalone/merged completion and no benign
  proxy harm. Security probe confirmed DNS and child processes blocked and wrapper result survives cwd changes.
- All **432** full replay/scoring cases completed; **48** task variants, **3** paired insertion positions
  and **3** routes. No incomplete cases were excluded. The dev pilot is separate (**108** cases).
- Replay invariants passed on all **144** route triplets: benign event streams and attack-piece positions
  agree across routes. Generated wording and executable arguments remain separate.
- Collection sources and the full runner match the recorded protocol/amendment hashes. Reporting-only
  additions are tracked separately. Runtime image IDs and dependency versions are in the ignored run artifacts.
- Primary report, figure and descriptive audits have been generated. The final safety figure was visually
  inspected for layout and labels. Supplementary benign validation completed with the primary thresholds
  unchanged. Realized audit rates differ across maps and routing strata; the report makes no equal-cost claim.

## Setup corrections and scientific boundaries

Worker outputs initially violated the JSON/path restrictions. Before collection, strict validation,
JSON-schema requests and path masking in wording-only inputs fixed the issue; invalid attempts remain
cached. Executable arguments were not changed by wording generation.

The six-task dev pilot selected plain wording and had an inconclusive H0 interval. The initial CLI had
incorrectly used dev H0 to block the full sample. A separate amendment recorded before any evaluation
scores restored the proposal's order: dev selects wording, full-sample H0 gates H1. Original pilot/gate
artifacts and the initial amendment were preserved. No scoring prompts, maps, seeds or decision rules
were retuned during evaluation.

The full sample passed H0; H1 is untestable in every family under the fixed private-gain ceiling rule.
See the report for estimates, paired intervals and counts. The scripted structure, first-piece placement,
missing task semantics, padded calibration mismatch, speculative tracing and nominal-budget limitations
are explicitly documented in `EXPLORATORY_V2_DESIGN_ISSUES.md`, the live tracker and the report.

Semantic-neighbor judging, stretched spacing, the second judged wording arm and live transactional
blocking remain deferred. They are not represented as completed experiments.

## Freeze audit

| Check | Status | Evidence |
|---|---|---|
| Original frozen config | PASS | No diff from `fd6b760` in `configs/frozen.yaml` |
| Protected scoring paths | PASS | No diff from freeze in maps, judge, streams, replay, stats or `run_experiment.py` |
| Original project/report | PASS | Original PROJECT archived byte-identically; frozen report unchanged |
| Label hiding | PASS | New deployable maps receive visible events only; invariance tests pass; oracle alone reads hidden labels |
| Sandbox | PASS | `--network none`, no host mounts, read-only root, resource limits and successful runtime probes |
| Secrets/generated files | PASS | No tracked `.env`, `logs/`, `cache/` or `.venv/` |
| Tests and smoke | PASS | 43 tests, scoped Ruff and sandbox checks above |
| References | PASS | PROJECT section 13 retains the approved list exactly; no unverified proposal references adopted |
| Budget authorization | PASS with recorded exception | User explicitly superseded the earlier $20 cap; live account-credit guard reserves retries/in-flight costs |
| Repository-wide Ruff | FAIL outside v2 | Existing sandbox style findings and an unrelated worker syntax edit; v2 paths are clean |

The unrelated `agents/worker.py` edit removed `try:` before tool-argument JSON parsing, leaving an indented
body and unmatched `except`. Restoring that line is the exact syntax fix. It was left untouched because
it appeared during this task and the v2 pipeline does not use that loop. The original sandbox also has
existing import/context-manager/broad-exception lint findings. These do not block this v2 evaluation.

No frozen parameters, protected scoring paths, old results or cache entries were changed. No real data,
credentials, network or host mounts were added to sandbox execution. No commit, push or external publication
was performed. Final local results and supplementary progress are linked above.

Final numerical validation, source hashes and reporting-source snapshot are preserved under `logs/exploratory_v2/602c1b9a2cff/`. The local report contains a claim → number → source table. All model-call processes finished; no external upload or commit was made.
