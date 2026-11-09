# Exploratory v2 design and execution issues

These limitations apply to this run even if all engineering checks pass. This is an exploratory
extension, not a replacement pre-registration for the original experiment.

- **Scripted behavior:** the worker generates descriptions of fixed requests. It does not choose
  actions, write executable code, or react to tool results. Conclusions concern monitoring these
  scripted proxy attacks, not autonomous or adaptive swarms.
- **Piece placement:** each attack root performs its piece before its two cover requests. Thus
  the per-agent group at an attack piece contains only that request, just like singleton review.
  Their calibrated thresholds can still differ because benign episodes include longer same-root
  histories. Singleton/per-agent safety differences must not be attributed to extra attack context.
  A post-result check confirmed identical scores on all 1,296 paired attack-piece requests across
  432 streams; the observed safety differences between these two maps come from calibration.
  This limits generalization to attacks embedded later in an agent's legitimate work history.
- **Speculative tracing:** the current request's runtime paths come from offline execution. A live
  transactional trace-before-commit control is not implemented.
- **Perfect auditor and no blocking:** the protocol assumes every audited attack piece is caught
  by an ideal auditor. Auditor accuracy and actual prevention are not measured. All requests run
  during replay; reported safety is the counterfactual routing of pieces to ideal review.
- **Task semantics available to the judge:** the judge does not receive seeded job source or full
  baseline file contents. In particular, the audit proxy checker treats numeric level 45 as audit,
  but the generic judge prompt does not explain that task-specific convention. Weak oracle results
  can reflect missing environment semantics as well as reasoning failure; they cannot be attributed
  solely to grouping quality or judge capability. The fixed judge prompt is retained during this run.
- **Fixed templates and family-specific worlds:** 16 parameterizations per family are variations
  of three fixed mechanisms. Each family has its own 200-episode calibration/evaluation backgrounds;
  this is not a single mixed-family population of 200 episodes.
- **Generic task structure and identifiers:** all three implemented families use the same abstract
  append-rule → seeded preparation → registration chain. Runtime reads are indirect in all families,
  whereas the proposal distinguished label preparation from named-config hand-offs. Requests also
  share opaque job identifiers. An exact-identifier grouping baseline was not evaluated; this run
  cannot establish that tracing is necessary or superior to every provider-computable grouping rule.
- **Disguise is narrow:** wording changes while executable arguments and neutral job namespaces
  are held fixed. Literal paths are masked only in the wording-generation prompt; the judge sees
  actual paths in the rendered requests and harness metadata.
- **Provider output compliance:** generation initially returned fenced JSON, malformed JSON, and
  literal paths despite instructions/schema. Strict local validation stopped those attempts.
  Fences are normalized, an exact-length JSON schema is requested, and path spellings are hidden
  from wording-only inputs. Invalid outputs are not silently accepted. Old attempts remain cached.
- **Gate placement correction:** the initial CLI incorrectly required a positive H0 confidence interval
  on the six-task dev sample before scoring evaluation. The imported proposal uses dev to select
  wording and tests H0 on the full evaluation before H1. This was corrected in a separate execution
  amendment before any evaluation scores. The inconclusive pilot is preserved; plain wording stays
  fixed. If full-sample H0 fails, H1 is untested and linkage is the headline. Individual pieces can
  already be suspicious, so a larger sample alone need not establish a joint-review benefit.
- **Padded control:** retaining own-root history can make matching provenance size and root count
  impossible. Report observed matching rates separately for attack pieces and benign calibration
  requests rather than claiming an exact match for every group. The first available calibration
  audit found only 334/1,800 joint matches in audit_off. This is an observed limitation, not a reason
  to change the control after scoring has begun; the final audit covers every family.
- **Audit budgets and ties:** a strict calibration quantile need not yield exactly the nominal held-out
  audit fraction. Primary evaluation scores only pieces' groups. It does not establish held-out benign
  audit rates without separately judging the benign evaluation stream. A supplementary benign-only
  reference validation completed separately using unchanged thresholds. Even after that check, actual
  audit rates across all attack-containing interleavings are not established. q measures flagged
  request frequency, not total judge tokens, unique context requests or actual auditor labor.
- **Global versus conditional budgets:** the primary result prompted a separate exploratory routing-stratum
  diagnostic. Calibration mixes 10% low-sharing, 40% high-sharing and 50% own-file benign episodes;
  none touches the attack's private file. One global threshold can allocate audits unevenly across
  these contexts, even when the overall calibration fraction is exactly 2%. The diagnostic preserves
  that threshold and is explicitly post-result; it cannot establish a causal dilution effect at
  equal conditional audit cost. Own-file episodes provide private analogues, not private-attack rates.
- **Integrity rule:** benign cross-root chains are chosen by the generator; the deterministic rule's
  flag rate depends directly on that choice. Catching all scripted attacks does not establish an
  affordable rule for real deployments.
- **Replication:** three insertion positions share a task and are averaged before task bootstrap;
  they are not three independent attacks. Report task counts and insertion counts separately.
- **Conditional uncertainty:** calibration bootstraps resample episode IDs and their already-scored
  groups from a fixed trace; they do not regenerate the benign world or rebuild its graph. Shared-file
  groups can span episodes, creating dependence beyond an episode cluster. The reported intervals
  describe this task/calibration resampling procedure, not uncertainty over all possible traffic
  populations, graph realizations, attack mechanisms or model pairs.
- **Family-wise inference:** H1 contrasts are reported per family with exploratory 95% intervals,
  not as three multiplicity-adjusted confirmatory discoveries. No unverified power claim from the
  imported proposal is adopted; there are 16 task variants per family, not 48 per family.
- **Oracle:** this is a reference grouping with a fallible judge, not a mathematical safety ceiling.
  Any map exceeding it needs explanation rather than suppression.
- **Scope:** semantic-neighbor judging, stretched spacing, and adaptive routing beyond h are not
  part of this Stage A run. No unverified references from the imported proposal are adopted.

Runtime discoveries, the gate outcome, budget stops and final measured diagnostics are added to
`RESULTS_LIVE.md` and `report/exploratory_v2.md`. No safety point estimates are reported from partial
or incomplete scored task pairs.
