# Handoff: updating the paper

For the next Claude instance. Deadline: **Mon Nov 9, 2026, 6:59 AM ET** (Apart Swarm Alignment Hackathon, 11:59 PM AoE).
Authors: Brandon Cardamone, Will Morrill. Never add Claude as a git co-author; never print or commit `.env`.

## The paper

- **Source of truth (local only, gitignored):** `report/paper_final.md`. This is the deslopped, cut-down version
  (~6 pages excluding abstract and references; 231-word abstract; 8-page cap).
  - Backups: `report/paper_final_pre_deslop.md` (pre-deslop) and `report/paper_final_long.md` (long, pre-cut).
- **Build the submission .docx:**
  ```bash
  uv run python scripts/fill_apart_template.py \
    "/mnt/c/Users/bcard/OneDrive/Desktop/Projects/Swarm alignment hackathon/Paper/Brandon Cardamone, Will Morrill - Apart Research hackathon submission template.docx" \
    "report/Who Draws the Map - final (deslopped).docx"
  ```
  Then copy the output into that `Paper/` folder. Current copy:
  `Paper/Brandon Cardamone, Will Morrill - Who Draws the Map (final, deslopped).docx`.
  The filler maps `#` headings to the template's styles, puts the title, authors and abstract into the header table,
  and embeds `![…](figures/…png)` images at 6.3 in. Bold lead-ins `**Implications.**`, `**Limitations.**` and
  `**Future work.**` become Heading 3.
- **Figures:** `uv run python scripts/paper_figures.py` regenerates all figures, drawn entirely in matplotlib. The
  paper uses figures 1–4:
  - Figure 1 = `fig1_setup`
  - Figure 2 = `headline`
  - Figure 3 = `fig3_h0_replication`
  - Figure 4 = `fig5_allocation` (`fig4_sharing` is unused after the cut)
  
  Exploratory numbers are hard-coded in that script, copied from the reports below.
- **Still to fill:** Will Morrill's affiliation (`[Affiliation]`); confirm the Author Contributions line.
- **Style rules applied (deslop skill, github.com/stephenturner/skill-deslop):** no em dashes or arrows, no
  bold-first bullets, active voice with "we", specific claims, varied rhythm. Keep them when editing.

## Studies and where their numbers live

1. **Frozen run (pre-registered, the primary evidence).**
   - Setup: autonomous DeepSeek V4 Flash agents; Mistral-Small-24B judge; 70 attacks.
   - Parameters committed before scoring: `configs/frozen.yaml`, commit `fd6b760`.
   - Results: `results/summary_preregistered.md`; exploratory equal-exposure re-analysis in
     `results/summary_exposure_EXPLORATORY.md`; tracker `docs/RESULTS_FROZEN_FINAL.md`; brief `docs/PROJECT_FROZEN.md`.
   - Findings: H0 supported (oracle 79% vs per-agent 25%, +54 pp); H-main and H-dilution not supported; the random
     control's lead is an exposure artifact.
2. **v2 (exploratory, Will).** Scripted agents, 432 streams. Report: `report/exploratory_v2.md`.
3. **v2.1 (exploratory, Will).** Adds an environment brief, cover history, an exact random control, and size-bin vs
   global thresholds.
   - Report: `report/exploratory_v21.md`; protocol `docs/V21_PROTOCOL.md`.
   - Post-hoc common-threshold addendum: `docs/V21_COMMON_THRESHOLD_ADDENDUM.md`.

Paper narrative: joint review replicates across all three runs (+23 to +56 pp). Audit allocation (catch rule and
threshold policy) moves safety by up to 100 pp on identical scores. Context still matters under a common cutoff, and
small precise groups do best. Label exploratory claims as exploratory. Never pool the runs.

## Code map

- `src/swarm_oversight/`: gateway (logged tool calls, hidden labels kept separately), tools, sandbox (no-network
  Docker runner), `maps/` (singleton, per_agent, clustering, provenance, oracle, random_matched), judge (0–9,
  logprob-weighted), streams, replay, stats (paired cluster bootstrap); plus `exploratory_v2*` modules.
- `scripts/`: `run_rollouts.py`, `run_experiment.py`, `analyze.py`, `analyze_exposure.py` (frozen run);
  `exploratory_v2*.py` / `exploratory_v21*.py` (follow-ups); `paper_figures.py`, `fill_apart_template.py`.
- Tests: `uv run pytest -q` (74 pass). Raw logs and the LLM cache are in gitignored `logs/` and `cache/`.

**Caution:** `scripts/live_status.py` writes the old frozen-run tracker over `RESULTS_LIVE.md`, which now holds the
merged v2.1 tracker. Don't run it, or restore the file afterwards with `git checkout -- RESULTS_LIVE.md`.
