# Exploratory v2 setup and execution

This is a separate experiment based on `docs/v2_pitch.md`. Its candidate config is
`configs/exploratory_v2.yaml`; never edit `configs/frozen.yaml` to run it.

## Local prerequisites

```bash
uv sync --extra dev --locked
docker build -t swarm-runner:0.1 -f sandbox/runner.Dockerfile sandbox
docker build -t swarm-runner-v2:0.1 -f sandbox/v2/runner.Dockerfile sandbox
```

Docker Desktop must be running. Both images use no-network containers, a read-only root filesystem,
resource limits and tar input/output, with no host mounts. V2 additionally rejects child processes.
No model-written code is executed by the host. Generated wording cannot modify executable arguments.

This local Docker daemon later returned a false missing-image response when inspecting these tags,
while listing them and running both smoke suites successfully. Inspection by the full image ID works.
If `preflight` reports a missing tag on this machine, check `docker image ls --no-trunc` and inspect
the listed ID before rebuilding. This diagnostic issue did not interrupt replay or validation; the
recorded collection CLI was preserved during the run.

If `.env` does not exist, copy `.env.example` to `.env` locally, then set `OPENROUTER_API_KEY` in an
editor. Do not paste credentials into chat or the terminal command history. The configured roles all
use OpenRouter; no separate DeepSeek, Groq or Google key is currently needed. Preflight prints only
whether a key is present. The worker and judge passed budgeted compatibility probes; the optional
embedder endpoint remains unverified.

The agent environment may use `uv --cache-dir /private/tmp/swarm-v2-uv-cache run --offline --no-sync ...`
after syncing dependencies, because the normal user cache is outside its writable sandbox. Normal
interactive terminal usage can use `uv run ...` throughout.

## Zero API-cost checks

```bash
uv run python scripts/exploratory_v2.py preflight
uv run python scripts/exploratory_v2.py plan
uv run pytest -q
uv run ruff check src/swarm_oversight/exploratory_v2 scripts/exploratory_v2.py sandbox/v2 tests/test_exploratory_v2.py
uv run python scripts/exploratory_v2.py smoke
uv run python scripts/exploratory_v2.py prepare --split dev
```

Smoke checks all three families and routing levels: no benign proxy harm, completion alone and after
merging, logged file effects, uncapped linkage and measured hub shares. It uses deterministic fixture
descriptions and is **not a model-safety result**. Batch execution happens inside Docker, one container
per stream. Smoke is a short check; a complete fixture replay is larger:

```bash
uv run python scripts/exploratory_v2.py prepare --split dev --fixture-text
uv run python scripts/exploratory_v2.py replay --split dev --fixture-text
```

## Paid dev pilot

`generate` makes one worker call per root, then saves descriptions separately from executable plans.
`replay` has no model calls. `judge` scores every calibration request under the five Stage A maps,
and only attack-piece requests in evaluation cases. Existing model responses use the normal SQLite
cache. A different grouping/path/prompt may require new calls; do not assume new conditions are free.

Paid commands require `--allow-api --estimated-cost-usd N --remaining-budget-usd N`. Replace N with
an estimated incremental cost and the verified remaining budget; these flags do not enforce a
provider-side spending limit. The CLI announces the estimate before calls. Configure an account-level
credit limit as appropriate. Start with dev; do not launch full evaluation from an untested candidate.

```text
uv run python scripts/exploratory_v2.py generate --split dev [budget flags]
uv run python scripts/exploratory_v2.py replay --split dev
uv run python scripts/exploratory_v2.py judge --split dev [budget flags]
```

Generation may fail schema validation; no tool executes until generation has completed. A dev gate
records the wording arm, H0 result, config and hash. The full runner preserves the pilot result but
tests H0 on evaluation before H1; an inconclusive dev interval is not a scoring prerequisite.
Dev tuning changes the protocol hash; finish tuning before
generating/scoring evaluation. The hypothesis test itself remains exploratory relative to the original freeze.

## Evaluation and outputs

```text
uv run python scripts/exploratory_v2.py prepare --split evaluation
uv run python scripts/exploratory_v2.py generate --split evaluation [budget flags]
uv run python scripts/exploratory_v2.py replay --split evaluation
uv run python scripts/exploratory_v2_full.py --run logs/exploratory_v2/<protocol-hash> --initialize-only
uv run python scripts/exploratory_v2_full.py --run logs/exploratory_v2/<protocol-hash> [budget flags]
uv run python scripts/exploratory_v2.py analyze --split evaluation
```

Artifacts live under `logs/exploratory_v2/<protocol-hash>/dev/` and `evaluation/`; fixture traces have
separate `fixture_dev/` and `fixture_evaluation/` directories. Protocol hashes include the config,
implementation, model roles and judge source. Traces also record wording hashes; mismatches fail
instead of reusing stale scores. Hidden labels are separate from visible events and reach only the
oracle map and evaluator. Completed cases resume at case boundaries. Do not clear `cache/`.

The JSON summary includes paired task/calibration bootstrap CIs and H0/H1 decisions. Completed primary
results are in `report/exploratory_v2.md`; the frozen report remains `report/draft.md`.

Reporting and supplementary checks use separate scripts:

```text
uv run python scripts/exploratory_v2_report.py --run logs/exploratory_v2/<protocol-hash>
uv run python scripts/exploratory_v2_design_audit.py --run logs/exploratory_v2/<protocol-hash>
uv run python scripts/exploratory_v2_benign.py --run logs/exploratory_v2/<protocol-hash> [budget flags]
uv run python scripts/exploratory_v2_live.py --run logs/exploratory_v2/<protocol-hash>
```

Only the benign validation command can make new model calls. It uses one held-out benign-only reference
interleaving and the existing calibration thresholds; it does not alter primary hypothesis decisions.
Run the report writer before the design-audit writer and append benign validation last: the primary
writer regenerates the main report. Preserve all run artifacts and the SQLite cache. Reporting scripts
produce the local Markdown, PNG/PDF figure and descriptive CSVs; they do not publish externally.

The initial CLI incorrectly required a positive H0 CI on the tiny dev sample. The full runner corrects
this before evaluation scoring: dev fixes the wording, full-sample H0 gates H1. It preserves the original
pilot and records immutable source/input hashes in an execution amendment. A budget guard includes
retry/in-flight reserves and reconciles usage against available account credits.
Use `--wait-for-replay` to overlap calibration scoring with the remaining isolated replay; case scoring
still requires all selected-arm cases. `RESULTS_LIVE.md` records this design correction explicitly.

## Scope and remaining limitations

- Semantic-neighbor embeddings, stretched spacing, the second judged arm and the optional unique-request
  budget remain deferred. The primary figure, q sweep and empirical nominal audit-budget equivalent
  are implemented. Account usage is measured; no exact per-run billed-cost claim is made.
- Initial worlds are family-specific (200 benign episodes per family per full split); this uses more
  background episodes than a single mixed-family pool. Do not describe it as one 200-episode mixed world.
- Wording changes descriptions, while neutral job namespaces and executable arguments are fixed.
  This is a narrower disguise manipulation than renaming all artifacts independently.
- The current request's runtime effects come from speculative offline tracing. A live transactional
  trace-before-commit monitor is not implemented. No online blocking effectiveness is claimed.
- Compatibility, completion, label invariance and paired replay checks passed. The full sample passed
  H0, while the private provenance-gain ceiling blocks H1 in every family. Padded matching is exact on
  attack pieces but often infeasible on benign calibration groups. Nominal q does not guarantee equal
  realized audit costs. The supplementary reference check cannot establish rates across every
  attack-containing interleaving. See the report for actual numbers and design limitations.
