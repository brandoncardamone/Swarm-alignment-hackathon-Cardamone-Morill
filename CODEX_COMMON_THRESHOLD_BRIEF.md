# Codex brief: common-threshold counterfactual (v2.1, exploratory addendum)

## Goal
Separate two effects in the v2.1 map comparison:
1. **Detection**: does a map change the judge's scores enough to change flags?
2. **Allocation**: does a map change flags only because its calibrated threshold differs?

Motivation: in 144/144 private first-piece cases, singleton, provenance and the exact random control get identical judge scores, yet produce 60/135/135 flags under size_bin. The gap comes from thresholds, not context. This addendum quantifies how much of every map difference is allocation versus detection.

## Hard constraints
- **No model calls.** Use only stored scores from `logs/exploratory_v21/7f98f60e29f5/`.
- Do not edit primary sources, `configs/frozen.yaml`, protected experiment code, existing reports or cached scores. Primary estimates and decisions stay unchanged.
- Label everything **post-hoc exploratory**. No new hypothesis tests and no superiority claims. Report descriptive counts and paired bootstrap CIs only, using the existing seed (20261108) and 2,000 replicates.
- Add tests under `tests/` for any threshold or flag recomputation logic. All existing tests must still pass.

## New files
- `scripts/exploratory_v21_common_threshold.py`: analysis script
- `docs/V21_COMMON_THRESHOLD_ADDENDUM.md`: write-up
- Outputs: `logs/exploratory_v21/7f98f60e29f5/common_threshold/` (JSON and CSV tables, plus a PNG for each figure)

## Steps

### 0. Verify the calibration mechanism
Using `exploratory_first_piece_calibration_diagnostic.json` and the calibration artifacts, report for each map (singleton, per_agent, size_root_matched, provenance, oracle), policy (global, size_bin) and family:
- the threshold for each size bin (1, 2–3, 4–9)
- the calibration support count for each bin
- whether each bin backed off to the global threshold (support below 50)
- the threshold actually applied to the 144 private first pieces

Confirm or reject this hypothesis: provenance and random's size-1 bin backs off to a lower, mostly larger-context threshold, while singleton's size-1 bin is fully populated and stricter. State the result plainly.

### 1. Common-threshold recomputation
Apply one shared threshold to all maps. Compute two variants:
- **A. Singleton threshold:** singleton's calibrated size-1 threshold at q=2%.
- **B. Pooled threshold:** the 98th percentile of pooled benign calibration scores across all five maps.

For each variant, map and family, report:
- private attack catches (stream-level, using the existing ideal-auditor piece-only catch rule)
- first-piece flags versus later-piece flags, separately
- held-out benign reference flag rate (flags/n and %). This is required: cost will no longer be about 2%.

Expected sanity check: under a common threshold, first-piece flags must be identical for singleton, provenance and size_root_matched. Fail loudly if they are not.

### 2. Allocation versus detection decomposition
For each map compared with singleton, and for provenance compared with size_root_matched, split the change in catches under the primary size_bin policy into:
- **allocation**: primary catches − common-threshold catches
- **detection**: common-threshold catches − the baseline's common-threshold catches

Present a single table. Include paired bootstrap CIs over the existing bootstrap groups.

### 3. Catch-versus-cost curves
For each map and family, sweep the threshold over the observed benign score range and plot private catch rate (y) against realized held-out benign flag rate (x). Mark the five existing q values. Use one figure per family, with all five maps overlaid. Also report:
- catch rate at matched realized benign rates of 1%, 2% and 5%, using interpolation, which you must state
- whether provenance's curve lies above size_root_matched's across the range, overlaps it, or crosses it (descriptive only)

### 4. Later-piece paired scores
For pieces 2 and later in private streams, report the paired difference in raw judge score (provenance − size_root_matched) on the same piece: mean, median and a bootstrap CI. This is the threshold-free test of "right context versus more context".

## Write-up (`docs/V21_COMMON_THRESHOLD_ADDENDUM.md`)
Keep it under about 1 page plus tables. Include:
- what was computed and why (2–3 sentences)
- the step 0 mechanism result
- tables from steps 1–2, the step 3 figures and the step 4 result
- a one-paragraph interpretation that separates detection from allocation
- limitations: post-hoc; ceiling (135/144 first-piece catches leave few streams where linkage can matter); fixed templated attacks; a single benign interleaving

Add a short pointer section to `RESULTS_LIVE.md` (no other edits to it) and regenerate it with the existing live script if that's how the file is produced.

## Done when
- The script runs end to end with no network access and no API calls.
- The sanity check in step 1 passes.
- Tests pass.
- The addendum and output tables exist, and the primary report numbers are byte-identical to before.
