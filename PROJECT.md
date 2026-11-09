# Who Draws the Map? Exploratory v2.1 structural follow-up

## 0. Active status

The completed v2 run is preserved in [report/exploratory_v2.md](report/exploratory_v2.md).
The new follow-up is on branch `exploratory/v21-structural-fixes`, with 62 passing tests and all nine
family/route Docker smoke checks passing. Full evaluation is authorized using remaining OpenRouter
credits. Announced estimate: $2–$6 and about 2–4 hours. No new keys or Docker setup are needed.
Live progress and design issues are written to [RESULTS_LIVE.md](RESULTS_LIVE.md). The complete primary
evaluation is in [report/exploratory_v21.md](report/exploratory_v21.md): 432 scored cases, all 15 calibration
and 15 reference batches, and both paired analyses. The judged identifier supplement is also complete:
all 432 cases, three calibration/reference families, both policies, and identical reproduced primary
estimates, CIs and counts. All model-call processes have finished.
Primary H0 is +22.92 pp [paired 95% CI 12.50, 37.50]; H1 remains untestable for audit logging, below
20 pp for label poisoning and inconclusive for configuration attacks. Strong private detection is
mostly first-piece flags, and final-piece provenance contexts retain all pieces in every stream; this is not evidence of joint
reasoning or a demonstrated linkage-loss effect. In 144/144 private first-piece cases, singleton,
provenance and the exact control have identical single-request scores but produce 60/135/135 flags;
the additional 75 provenance flags arise from threshold allocation. The identifier comparator catches
48/48 configuration cases on every route under the primary policy; no paired superiority test was
specified. Approximate account-usage increase: $2.00; verified remaining credits: $21.93.
Provider throttling required a paced, transport-only
resume with unchanged scientific sources, requests and inputs.

## 1. Fixed follow-up specification

[docs/V21_PROTOCOL.md](docs/V21_PROTOCOL.md) is the complete collection specification, hashed with the
source before new model collection. This is exploratory development informed by v2, not a change to
`configs/frozen.yaml`. The previous v2 project and tracker are archived in
[docs/PROJECT_EXPLORATORY_V2.md](docs/PROJECT_EXPLORATORY_V2.md) and
[docs/RESULTS_EXPLORATORY_V2.md](docs/RESULTS_EXPLORATORY_V2.md). The original frozen project remains in
`docs/PROJECT_FROZEN.md`; its protected experiment code and report remain untouched.

## 2. Structural changes

- One uniform, public environment brief gives the judge the missing task semantics, without hidden
  request labels. Judge model, score extraction and fallback are unchanged.
- Every benign/attack triple runs as cover-read → operation → cover-write, so per-agent review has
  earlier own-root context at each piece. Request count and trusted seed construction stay fixed.
- A current-request-anchored random prefix control exactly matches provenance size/root count. It
  replaces the often infeasible padded-history control; capacity fallback frequency is reported.
- Primary calibration uses visible size bins 1, 2–3 and 4–9, with global backoff below 50 calibration
  requests. The original global-threshold policy is reported alongside it from the same scores.
  This is a new audit-allocation policy. Realized benign reference rates are measured; equal actual
  audit cost is not assumed. Both policies retain the original H0/private-gain/H1 decision order.

## 3. What stays fixed

Same model pair, M=9, h=2, cap=8, seed 20261108, three proxy mechanisms, 16 variants per family,
three routes, three insertion positions, 200 calibration/evaluation benign episodes per family,
plain wording, primary q=2%, five q values, 2,000 paired bootstrap replicates and ideal-auditor
piece-only catches. The same no-network/no-host-mount Docker image is reused. Benign wording is
reused; fresh attack variants use indices 216–231, disjoint from the examined 200–215. These are new
parameterizations of the same mechanisms, not new independent attack mechanisms.

## 4. Outputs and execution

New code is in `src/swarm_oversight/exploratory_v21/`, collection in
`scripts/exploratory_v21.py`, config in `configs/exploratory_v21.yaml`, and artifacts in
`logs/exploratory_v21/<protocol-hash>/`. Original v2 sources, results and model cache are preserved.

```bash
uv run python scripts/exploratory_v21.py smoke
uv run python scripts/exploratory_v21.py prepare
uv run python scripts/exploratory_v21.py run --allow-api --estimated-cost-usd 6 --remaining-budget-usd 23.92
```

The runner refreshes actual account credit/usage and model prices before calls, reserves retry and
in-flight costs, saves complete calibration/reference/case checkpoints, and verifies collection-source
hashes. No credit purchases, commits, pushes or external publication are performed. Results are local.

Regenerate the completed report, supplementary tables and live tracker without model calls:

```bash
uv run python scripts/exploratory_v21_report.py --run logs/exploratory_v21/7f98f60e29f5
uv run python scripts/exploratory_v21_live.py --run logs/exploratory_v21/7f98f60e29f5
```

## 5. Interpretation limits

All four changes are bundled; improvements cannot be causally assigned to one without an ablation.
Comparisons with the previous v2 run are descriptive because the follow-up also uses fresh variants.
Public semantics may make some pieces suspicious alone. A new run can still fail H0 or the private
20 pp gain prerequisite, and such outcomes will be retained. Fixed scripts, three templates, one model
pair, speculative tracing, a perfect auditor, one benign-only reference interleaving, and calibration
bootstrap dependence remain limitations. The judge sees generated descriptions (capped at 700 characters),
tool names and logged paths, not raw arguments or file contents. Size-bin calibration is not a guarantee of equal held-out
rates, conditional routing cost, judge tokens or auditor labor. Stage B remains unevaluated.
A separate [identifier linkage diagnostic](docs/V21_IDENTIFIER_ADDENDUM.md) and
[judged identifier supplement](docs/V21_IDENTIFIER_JUDGED_ADDENDUM.md) were specified before primary
attack-piece scores were available. The judged supplement follows the full primary evaluation and
appends results without changing primary estimates or decisions. No unverified proposal references
are adopted.

## 13. References (retained approved list; no additions)

Brown et al. 2026 (arXiv 2605.31593) · Makins et al. 2026 (2607.07368) · Sun et al. 2026 (2608.17445) · Chen et al.
2025 (2506.10949) · Rose et al. 2026 (2604.01151) · Cai et al. 2026, NeuroTaint (2604.23374) · Greenblatt et al. 2024
(2312.06942) · Hills et al. 2026 (2607.02514) · Remedios et al. 2026 (2609.19587) · Kothamasu et al. 2026,
DecompBench (2606.13994) · Kravchenko et al. 2026, APPA (2607.24625) · Debenedetti et al. 2025, CaMeL (2503.18813) ·
Costa et al. 2025, FIDES (2505.23643) · Wang et al. 2026, MAP-Graph (2608.10509) · Wang et al. 2026, provenance survey
(2606.04990) · METR 2026 incident report · Swarm Traces 2026.
