# Exploratory v2.1 implementation and execution checkpoint

Branch: `exploratory/v21-structural-fixes`. The user authorized structural improvements, full evaluation
and all remaining OpenRouter credits. No commit, push, credit purchase or external upload was made.
Completed original v2 results, source hashes, traces and caches are preserved.

## Changes

| File | Purpose |
|---|---|
| `configs/exploratory_v21.yaml` | Separate fixed follow-up parameters and two calibration policies |
| `docs/V21_PROTOCOL.md` | Source-hashed protocol, hypotheses, rationale, budget and interpretation limits |
| `src/swarm_oversight/exploratory_v21/design.py` | Cover-first execution plan and exact label-blind size/root control |
| `src/swarm_oversight/exploratory_v21/judge.py` | Uniform public environment semantics with unchanged model/digit/fallback |
| `src/swarm_oversight/exploratory_v21/analysis.py` | Global/size-bin thresholds and paired task/calibration bootstrap |
| `src/swarm_oversight/exploratory_v21/__init__.py` | Separate exploratory namespace |
| `scripts/exploratory_v21.py` | Immutable-source collection, credit/pricing preflight, replay, scoring and both analyses |
| `scripts/exploratory_v21_report.py` | Complete-matrix validation, local report, figure, CSVs and descriptive audits |
| `scripts/exploratory_v21_live.py` | Local progress and design-issue tracker; no API calls |
| `scripts/exploratory_v21_transport.py` | Paced cached resume and bounded provider/network backoff |
| `src/swarm_oversight/exploratory_v21_identifier.py` | Label-blind grouping from canonical IDs in visible arguments |
| `scripts/exploratory_v21_identifier_audit.py` | Judge-free identifier linkage diagnostic |
| `scripts/exploratory_v21_identifier_eval.py` | Complete prospective supplementary evaluation and report appendix |
| `docs/V21_IDENTIFIER_ADDENDUM.md` | Separate post-launch judge-free diagnostic scope |
| `docs/V21_IDENTIFIER_JUDGED_ADDENDUM.md` | Prospectively declared judged supplement and unchanged-primary check |
| `tests/test_exploratory_v21.py` | Structural, label invariance, calibration, inference and deduplication tests |
| `tests/test_exploratory_v21_report.py` | Reject partial/invalid reports and avoid partial safety claims |
| `tests/test_exploratory_v21_identifier.py` | Visible-only identifiers, boundary behavior and prefix selection |
| `tests/test_exploratory_v21_transport.py` | Cache bypass, concurrency limits and transient-error handling |
| `pytest.ini` | Restrict discovery to actual tests, excluding archived test source copies |
| `PROJECT.md`, `README.md` | Point to active follow-up and preserved earlier results |
| `docs/PROJECT_EXPLORATORY_V2.md`, `docs/RESULTS_EXPLORATORY_V2.md` | Exact prior project/tracker archives |
| `RESULTS_LIVE.md` | Current follow-up progress, decisions and limitations |
| `report/exploratory_v21.md` | Complete local findings, counts, CIs, supplement and design/runtime issues |
| `report/figures/exploratory_v21_7f98f60e29f5_safety.{png,pdf}` | Verified actual two-policy primary figure |
| `analysis/exploratory_v21/` | Summary JSONs, 90 primary + 18 supplementary safety cells, 540 descriptive q-sweep cells and verification |

The unrelated original worker syntax edit and other pre-existing working-tree changes remain untouched.

## Engineering validation

- `uv run pytest -q`: **62 passed**, including all original tests. No model calls.
- Scoped Ruff for the new modules/scripts/tests: **passed**. `git diff --check`: **passed**.
- Cover-first Docker smoke: **nine family/route cells passed**, with no benign proxy harm, successful
  merged attack completion, prior own-root history and exact control matching. The existing security
  probe passed DNS/process/cwd checks. The original sandbox smoke also passed all nine checks.
- All **432** follow-up replays completed. An independent replay audit verifies **144** private/low/high
  triplets with identical benign events and attack-piece positions. All **1,296** per-agent piece
  contexts contain two own-root requests; all **1,296** matched piece contexts match size and roots.
- Generation completed **64** successful new calls plus **80** cache hits for fresh attack roots;
  17,462 prompt and 2,976 completion tokens, from the collector's generation-stage counters.
  Benign descriptions were reused, not regenerated. These are operational counters, not safety results.
- Generated data hashes were recorded after generation and before any attack-piece scoring. The
  collector generates all wording before starting replay/judging; input-freeze timing is explicitly
  recorded, including calibration batch count. Reporting verifies those hashes independently.
- Collection source/config/protocol hashes were recorded before calls and are checked by the runner.
  Reporter/live code is separate so reporting changes cannot alter the scoring process.

## Freeze audit and budget

| Check | Status | Evidence |
|---|---|---|
| Frozen configuration | PASS | No diff from `fd6b760` in `configs/frozen.yaml` |
| Protected original scoring code | PASS | No diff in maps, judge, streams, replay, stats or `run_experiment.py` |
| Completed v2 collection sources | PASS | All 28 protected v2 source/config/dependency hashes match the earlier snapshot |
| Label hiding | PASS | Exact control accepts only visible events/target sizes/roots; hidden-label invariance test passes |
| Sandbox | PASS | Original image reused, no network/host mounts; actual security and replay checks pass |
| Secrets/cache | PASS | No `.env` contents printed or copied; generated run data and persistent cache stay ignored |
| Account authorization | PASS with recorded exception | User explicitly superseded former $20 cap; about $23.93 verified available at launch |
| References | PASS | Approved PROJECT section 13 retained; no imported unverified proposal claims adopted |
| Repository-wide Ruff | Existing failure outside follow-up | Original sandbox style findings and unrelated worker.py missing `try:` remain documented |

The archived-test discovery clash was caused by copying tests into a provenance snapshot beneath logs.
The new `pytest.ini` includes the complete actual `tests/` directory without collecting generated
archives. No test or assertion was deleted, and no cache or old log was cleared.

## Active run

Run: `logs/exploratory_v21/7f98f60e29f5`. Primary collection, both paired analyses, the full judged
identifier supplement and local reporting are complete. Deliverables are
`report/exploratory_v21.md`, scientific figure/CSV outputs and `RESULTS_LIVE.md`. All 15 calibration
batches (27,000 rows), all 15 reference batches (27,000 rows), and all 432 attack cases pass completeness
and score checks. All 90 primary safety cells reproduce their raw counts, and source/input hashes match.
Size-bin calibration is a new policy, not a retroactive rescue of v2. Both policy outcomes will be
reported, including failures of H0 or the private-gain prerequisite. See the fixed protocol for scope.

## Supplementary structural diagnostics

A post-generation wording screen found 17 temporal-language matches, including 13 reused benign read
descriptions. Some refer to post-operation checks although cover reads now come first. Structured
arguments and actual execution remain correct. The fixed wording was retained; these are a corpus-
quality limitation, not automatically 17 semantic errors. The screen is preserved in the run artifacts.

The post-launch, judge-free identifier addendum uses only job IDs in visible argument values. It links
all three pieces in 432/432 replays (144/144 per route), with mean size 5 and precision 0.6. No additional
model calls or primary changes were made. This does not establish judge safety or audit affordability.
Added source/test files are `src/swarm_oversight/exploratory_v21_identifier.py`,
`scripts/exploratory_v21_identifier_audit.py`, `tests/test_exploratory_v21_identifier.py`, and the separate
`docs/V21_IDENTIFIER_ADDENDUM.md`. Primary collection-source hashes still verify unchanged.

The full report formatter was exercised with synthetic zero scores in a temporary directory: 90 primary
CSV cells, 450 descriptive q-sweep cells and the two-policy figure rendered successfully. Temporary
fixture outputs were deleted and are not scientific results. The actual primary report, figure and
CSV outputs are now written; the real figure was visually inspected successfully.

## Provider transport recovery

Provider HTTP 429 exhausted existing retries after 11 calibration batches. The original collector
stopped with all replay/score checkpoints and cache intact; no attack-piece outcomes had been scored.
A single uncached readiness request then succeeded. The same frozen collector resumed through
`scripts/exploratory_v21_transport.py`: initial concurrency 8, 0.35-second start spacing, at most three
wrapper attempts with 30-second pauses and reduced pressure on later attempts. This is a scheduling-only
amendment; scientific code, requests, thresholds, models and inputs remain unchanged. The live tracker
now detects stopped collector PIDs/backoff, with regression tests. All 62 tests pass.

After the first held-out batch, transport resumed at 16 concurrent requests and 0.2-second start
spacing, with bounded 8/0.4-second and 4/0.8-second fallbacks. The same settings were applied to the
queued identifier supplement before it began. Both scheduling amendments are recorded separately;
successful responses remain cached and the scientific sources/inputs are unchanged.

A separate judged identifier supplement ran after the complete primary summary, with prospective
source hashes, same traces/judge/policies, and an additional $0.50–$1.50 estimate. It must reproduce every
original primary estimate/CI identically. Its results append to the local report; no primary decisions
were changed. All 432 cases and three calibration/reference families are complete. Source: `scripts/exploratory_v21_identifier_eval.py` and
`docs/V21_IDENTIFIER_JUDGED_ADDENDUM.md`.

## Completed result review

All 90 primary and 18 identifier safety cells reproduce raw counts. Every original primary estimate,
CI, count and hypothesis decision is identical in the six-map supplementary analysis. Both primary
source/input hash checks pass. CSV/JSON exports and a machine-readable verification record are in
`analysis/exploratory_v21/`. The full local report includes both policies, all families, confidence
intervals, audit rates, control checks and runtime/design issues.

The primary H0 gain is 22.92 pp [95% CI 12.50, 37.50]. H1 is untestable for audit logging, below 20 pp
for label poisoning and inconclusive for configuration attacks (D 14.58 pp [−20.83, 45.83]). Strong private
detection does not establish joint reasoning: 135/144 provenance first pieces are flagged, and the exact
random control catches 137/144 versus provenance's 141/144 private streams. Final-piece provenance
contexts retain all pieces after the cap in 432/432 streams, so there is no observed linkage-loss example.

A reproducible, explicitly post-collection diagnostic finds identical single-request first-piece
scores in 144/144 private cases, but 60/135/135 flags for singleton/provenance/exact control because their
size-bin cutoffs differ. The extra 75 provenance flags at that decision arise from audit allocation,
not additional context. No policy was refitted. Identifier selection links all pieces without runtime
tracing and catches 48/48 configuration attacks on every route under size-bin calibration; its judge
still receives common logged paths, and no paired superiority test was specified.

Latest verified account usage is $8.0714, including prior work, versus $6.0710 at launch: approximately
$2.00 incremental usage and $21.93 remaining. This is an account delta, not an exact per-run bill.
All 62 tests and scoped v2.1 Ruff checks pass. Repository-wide Ruff retains 15 existing sandbox style
and unrelated worker syntax findings. Original frozen/v2 sources and reports remain preserved.
No new keys or Docker setup were needed. No commit, push, external publication or credit purchase occurred.

The final image audit reproduced the known Docker tag-inspection quirk in `docs/V2_SETUP.md`; tag listings and full-ID inspection match both prelaunch image hashes. No rebuild was needed. Credential-pattern, frozen-path and final source/input hash checks pass. All model/reporting processes have exited; final live tracker refresh is complete.
