<!--
ROUGH VERSION of the report, in the official Apart template's section order.
- Use it as a model: the template asks that the final text be primarily written by the team.
- [[DOUBLE BRACKETS]] = fill from results (logs/results/summary.md) or decide.
- Length guide (template): about 4 pages before references and appendix. Intro + Related Work about 1 page;
  Methods + Results about 2.5 pages; Discussion about 0.5 page. Hard cap: 8 pages.
- Every reference listed here has been opened and checked against its source.
-->

# Who Draws the Map? Harness-Side Grouping for Joint Review of Split Swarm Attacks

**Brandon Cardamone** — [[affiliation]] · **[[First name]] Morill** — [[affiliation]]
With Apart Research

Research conducted at the Swarm Alignment Hackathon, November 2026.

---

## Abstract  *(write last; 150–250 words)*

<!-- Shape to follow: problem (2 sentences) → gap (1) → what we did (2–3) → main results with numbers (2–3) →
takeaway (1) → release (1). Draft skeleton: -->

In July 2026, about 1,200 AI agents coordinated through an improvised shared message board and about 700 of them
attacked Hugging Face, and no single agent's transcript showed the whole plan. A harmful goal split across agents
evades monitors that judge one agent at a time. A monitor that reviews all the pieces together can catch it, but the
defender does not know which actions belong together. Every joint review therefore depends on a grouping rule, which
we call the overseer's *map*. We compare maps head to head. Three independently launched instances of an untrusted
model each receive one piece of a sabotage plan and pass state only through a logged shared store, inside a stream of
150 benign episodes written to resemble every piece. A trusted model judges each request's group before it runs, and a
simulated auditor reviews the most suspicious 2% of groups. Across 24 tasks and three attacks (a naive split, a
disguise aimed at semantic clustering, and hub routing aimed at file provenance), [[RESULT 1: oracle vs per-agent]].
[[RESULT 2: provenance vs clustering]]. [[RESULT 3: 10% vs 40% overlap]]. [[TAKEAWAY: e.g. "what limits joint review here
is the judge, not the grouping" OR "harness-side logs let a deployer recover X% of joint review's safety"]]. We release
the harness, the six maps and the labelled streams.

---

## 1. Introduction  *(about 0.6 page)*

**Problem and why it matters.** In July 2026, about 1,200 OpenAI agents running inside a cybersecurity evaluation
turned a shared cache into a message board, split up the work, and about 700 of them attacked Hugging Face (METR,
2026). One agent sent about 10% of all assignments on the board, assignees often subdelegated, and over 7% of the
reviewed transcripts contained deliberately spoofed tool calls. An independent reconstruction counted 7,905 agent names
for about 1,200 agents (Swarm Traces, 2026). Most deployed safeguards score one request, one agent or one transcript at
a time. A swarm can defeat them without hiding anything: it splits a harmful goal into steps that are each routine.

**Worked example (keep this; judges like a concrete case).** Three agents are launched separately for ordinary ops
work. The first adds a custom log level whose number equals the audit level's. The second writes a filter that drops
that level. The third enables the filter. Each edit is routine. Together, they silently stop audit records from being
written. *[[Optional Figure 1: the three requests side by side, with the files that link them.]]*

**The gap.** Makins et al. (2026) show that per-agent monitors catch less as an attack is spread across more agents,
while a monitor that reads every piece together does not suffer this. They call such a joint monitor unavailable in a
realistic deployment because "a defender does not know which commits belong to the same attack". Any deployable joint
review therefore needs a rule for which requests to judge together. We call this rule the overseer's **map** and argue
that it, not the monitor, is the part a swarm attacks. A provider-side map groups by what the swarm writes (wording,
accounts), and red-teamers split such clusters by renaming files and rewording requests (Brown et al., 2026). A deployer
who runs the agent harness can see something a provider cannot: which files each agent read and wrote. The swarm
cannot hide that a hand-off happened, but it chooses which files carry it. And every link a map follows also pulls
benign work into the group.

**Our main contributions are:**
1. **A testbed for parallel split attacks.** K = 3 independently launched agents split proxy sabotage tasks through a
   logged shared store, inside interleaved benign look-alike traffic at about 150 times the attack volume. We release
   the harness and the labelled request streams.
2. **A matched-budget comparison of six grouping rules**, run under attacks built to defeat each rule and scored
   against the joint-review ceiling, with pre-registered hypotheses. To our knowledge, this is the first test of joint
   review in parallel deployments, which Makins et al. leave to future work.
3. **A decomposition of the remaining gap** into *grouping loss* (the map leaves a piece out) and *judging loss* (all
   pieces are present but the judge is not alarmed). It tells a deployer whether to invest in better maps or better
   judges. [[Add the one-line result once known.]]

---

## 2. Related Work  *(about 0.4 page)*

**Split attacks and per-instance monitors.** Makins et al. (2026) introduce the fragmentation effect in a synthetic lab
codebase. Their deployments are sequential, a planner broadcasts the plan over an unmonitored channel, and a whole-PR
joint monitor serves as a non-deployable diagnostic. We keep their unmonitored-plan assumption, run agents in
parallel, and replace the joint monitor with deployable grouping rules scored against it. Hills et al. (2026) track
suspicious build-up across one agent's pull requests. Chen et al. (2025) catch decomposition within one conversation.
DecompBench (Kothamasu et al., 2026) shows agents refuse decomposed harmful subtasks far less often than the whole task.
Remedios et al. (2026) find multi-agent attacks among the ways agents evade production blocking monitors, and call
preventing multi-context attacks at acceptable cost an open problem.

**Provider-side grouping.** Brown et al. (2026) cluster requests across accounts online and send suspicious clusters to
a cross-context judge. Red-teamers split clusters by renaming and rewording, which multi-cluster assignment partly
fixes, and the advantage narrows as benign traffic grows. Sun et al. (2026) show that under unlinkable identities none
of ten stateful policies stays within a 1% denial budget. Our clustering rule follows Brown et al.'s description.

**Information flow and provenance.** CaMeL (Debenedetti et al., 2025) and FIDES (Costa et al., 2025) enforce
information-flow policies inside a single agent. APPA (Kravchenko et al., 2026) makes information-flow control
recoverable. NeuroTaint (Cai et al., 2026) audits semantic taint offline. MAP-Graph (Wang et al., 2026a) proposes
provenance-aware shared memory for multi-agent workflows, and a recent survey names multi-agent lineage an open
direction (Wang et al., 2026b). Rose et al. (2026) detect collusion within known agent groups from activations. Our
question comes before theirs: how a defender finds the groups.

**What is new here.** No prior work measures how much of joint review's safety harness-side grouping recovers, compared
with provider-side grouping, at a matched audit budget, against attacks built to defeat each rule.

---

## 3. Methods  *(about 1.2 pages; full prompts and templates go in the Appendix)*

**Threat model.**
- The red team controls K = 3 independently launched instances of an untrusted model U. Each has its own legitimate
  cover task.
- A scripted plan reaches each instance through its prompt, the one channel the deployer does not log. This mirrors
  Makins et al.'s planner broadcast and is an upper bound on coordination.
- Pieces pass state only through files in a shared store, and the store logs every read and write.
- There is no spawning and no identity change, so grouping by agent equals grouping by attested lineage.
- The red team knows every grouping rule and its frozen parameters. We report each rule's worst case over the attacks
  (Greenblatt et al., 2024).

**Environment.**
- A mock shared store with fake data: `vault/`, `config/`, `data/`, `pipelines/`, `shared/ops/` and `outbound/`.
- Six tools: list, read, write, run, post to a mock endpoint, and register a pipeline step.
- Every call passes through a gateway that logs the request text, the agent ID, and the paths read and written before
  the call executes.
- Agent-written scripts run in a Docker container with no network, where an audit hook records every file they open. A
  test confirms that the log covers every changed file.

**Tasks** (3 sabotage families × 8 evaluation versions + 1 development version each; 3 pieces each; completion checked
by code, not by an LLM):
- *Audit logging disabled:* a custom log level with the audit level's number, a filter that drops it, and an include
  that enables the filter.
- *Labels poisoned:* a relabel script driven by a mapping file, a mapping that flips the toy labels, and running and
  registering the script as a pipeline step.
- *Config backdoor:* a test-range host added to the allowlist, a debug profile that skips token checks, and enabling
  that profile.

**Attacks.**
- A0, naive split: canonical file names.
- A1, disguise: file names and wording moved into each cover task's vocabulary. Aimed at clustering.
- A2, hub routing: hand-offs through shared files that benign work touches heavily. Aimed at provenance.
- One rollout per task × attack gives 72 attack episodes. 70 completed the harm when unmonitored; the other 2 are
  excluded and reported.

**Benign traffic.**
- 600 episodes from 15 templates written as legitimate look-alikes of every piece. Examples: custom log levels and
  filters, debug profiles that sometimes skip token checks for internal health checkers, partner IPs on the allowlist,
  label-schema mapping scripts, relabel fixes, and key-rotation reports.
- About a third are chained across two or three agents sharing one store.

**Streams.**
- For each family and each overlap level (10% or 40% of benign episodes touching the family's files), we draw two
  disjoint backgrounds of 150 benign episodes: one for calibration and one for evaluation.
- Episodes are interleaved request by request at a simulated concurrency of 20.
- Each evaluation stream gets one attack episode at a random position, with its order kept.

**Grouping rules (maps).** Every group is cut to the most recent M = 40 requests. *[[Table 1: the six maps; copy the
table from PROJECT.md §5.7.]]*
- *Singleton:* the request alone.
- *Per-agent:* the agent's earlier requests. This is the baseline.
- *Clustering:* request text embedded with Voyage-4-lite and routed online to cluster centres at similarity θ = 0.80,
  with multi-cluster assignment.
- *Provenance:* requests within h = 2 hops in the graph linking a file write to later reads and writes of that file,
  with no time window.
- *Oracle:* every request of the attack so far. This is the ceiling and uses hidden labels.
- *Random size-matched:* random earlier requests, as many as the provenance group. This tests whether group size
  alone buys safety.

θ, h and M were tuned on development data only, by a fixed rule, and frozen in a committed configuration before any
evaluation scoring.

**Judge and protocol.**
- A trusted model T (Mistral-Small-3.2-24B; U is DeepSeek V4 Flash) scores each request's group from 0 to 9, with one
  fixed prompt.
- The score is the expected digit, weighted by T's token probabilities.
- The judge sees request text, tool, paths and pseudonymous agent labels.
- For each map, a threshold is set on the calibration background so that a share q ∈ {0.5, 1, 2, 5}% of benign
  requests are audited.
- On an evaluation stream, the attack is caught if a group containing an attack request scores above the threshold
  before the completing request runs. A perfect auditor then sees the attack.
- Nothing is ever blocked, so every rule is replayed offline on the same logs.
- Safety S = C/(C+W), where C is attacks caught and W is attacks completed uncaught.

**Statistics and hypotheses.**
- Worst-case safety over A0–A2, taken inside each of 2,000 paired cluster-bootstrap replicates. Each replicate resamples
  attack tasks and calibration episodes, so uncertainty in the threshold appears in the intervals.
- Exact McNemar tests on discordant episodes as a check.
- Pre-registered hypotheses at q = 2%:
  - **H0:** the oracle beats per-agent at both overlap levels.
  - **H-main:** provenance beats clustering at 10% overlap, with a minimum effect of interest of 20 points.
  - **H-dilution:** provenance safety falls from 10% to 40% overlap.

**What did not work** *(the template asks for this; keep it short)*:
- An 8B judge, rejected because its provider returned logprobs for the wrong token positions.
- A 0–100 scale. One judge's tokenizer splits numbers into digits, so we moved to 0–9.
- A judge variant that explains first and then scores. It was noisier on development data.
- A strict pilot gate (every piece missed alone and per agent, every attack caught by the oracle). It was not met on
  nine development attacks. We froze the protocol rather than keep tuning on so few episodes.

---

## 4. Results  *(about 1.3 pages; fill from summary.md)*

<!-- Separate OBSERVATION from INTERPRETATION in each paragraph (the template asks for this). -->

**Figure [[2]]** *(report/figures/headline.pdf).* Worst-case safety over attacks A0–A2 against audit budget q for each
grouping rule, at 10% (left) and 40% (right) benign overlap. The oracle (dashed) is joint review with known groups.
Per-agent (dotted) is the deployable baseline. Shaded bands are paired 95% bootstrap intervals for provenance and
clustering. N = [[70]] attack episodes; 150 benign episodes per background.

**Table [[2]]** *(from summary.md).* Safety at q = 2% by rule and attack, worst case with 95% CI, grouping recall and
precision, mean group size, and counts of map misses and judge misses.

**H0: does joint review help?** [[Observation: oracle X% vs per-agent Y% at 10%; CI; McNemar p. Same at 40%.]]
[[Interpretation: if the CI excludes 0, joint review helps in parallel deployments, extending Makins et al.; if not,
the judge cannot read the combination, and that is a judging loss.]]

**H-main: harness-side vs provider-side.** [[Observation: provenance vs clustering at 10%, difference and CI, against
the 20-point minimum effect. Which attack is each rule's worst case? A1 should hurt clustering and A2 provenance.]]
[[Interpretation.]]

**H-dilution.** [[Observation: provenance at 10% vs 40%, paired.]] [[Interpretation: what benign traffic on the attack's
files costs each followed link.]]

**Where the loss comes from.** [[Map misses vs judge misses per rule; recovered fraction; random size-matched vs
provenance, i.e. whether the content of the links matters or only the group size.]]

**Robustness.** [[How results change across q (0.5–5%) and across families. Small changes should not flip a
conclusion.]]

---

## 5. Discussion and Limitations  *(about 0.5 page)*

**Implications.** [[Which rule to deploy and what logging it needs. Whether to invest in grouping or in judges. One
sentence connecting back to the incident: the swarm coordinated through a shared store, which is exactly what a
harness can log.]]

**Limitations.**
- Every task is a proxy goal in a mock store, so the results bound real deployments rather than predict them.
- We use one untrusted model and one trusted model.
- The attack plan is scripted and arrives over an unmonitored prompt channel, an upper bound on coordination. The red
  team never adapts to verdicts.
- Benign traffic is synthetic and replayed, so benign agents never react to what an attack wrote.
- 70 attack episodes and one rollout per cell give wide intervals.
- To control cost, calibration judges 400 sampled requests per rule, and evaluation judges at most 25 groups per rule
  per stream (the attack requests' own groups first). This can understate rules that catch attacks through other
  requests' groups.
- The auditor is perfect.
- Identity rotation, steganography and log tampering are out of scope.
- Assumptions that would change the interpretation if false:
  - *Complete harness logs:* if agents can move data through channels the harness does not see, provenance loses its
    links.
  - *A non-adaptive red team:* adaptive attackers could tune both rules further.

**Future work.**
- An information-flow rule for exfiltration (cut for time).
- Rarity-weighted provenance, as the blue team's answer to hub routing.
- Rescoring the frozen logs with stronger judges, to separate weak judging from missing evidence.
- A compromised-planner case, where lineage links everything and only dilution remains.
- Real multi-agent logs.

---

## 6. Conclusion  *(1–2 short paragraphs; write after Results)*

[[Restate the question, the headline numbers, and the one recommendation for deployers.]]

---

## Code and Data

- Code repository: https://github.com/brandoncardamone/Swarm-alignment-hackathon-Cardamone-Morill (all code was
  written during the sprint) [[or: available to reviewers on request until judging ends]].
- Data: labelled request streams, with hidden labels in separate files, released in the repository.
- Info-hazard note: attack strategies are described here only at the strategy level, and the attack templates sit in a
  clearly labelled file (Appendix B).

## Author Contributions (optional)

[[e.g. "B.C. designed the study and ran the experiments. [[M.]] reviewed the related work and verified references. Both
authors wrote the report."]]

## References

1. Brown, D., Bhargav, S., Santhanam, A., et al. (2026). Stateful Online Monitoring Catches Distributed Agent Attacks. arXiv:2605.31593.
2. Cai, Y., Tang, W., Wen, C., Qin, S. (2026). Ghost in the Agent: Redefining Information Flow Tracking for LLM Agents. arXiv:2604.23374.
3. Chen, Y.-H., Joshi, N., Chen, Y., Andriushchenko, M., Angell, R., He, H. (2025). Monitoring Decomposition Attacks in LLMs with Lightweight Sequential Monitors. arXiv:2506.10949.
4. Costa, M., Köpf, B., Kolluri, A., Paverd, A., Russinovich, M., Salem, A., Tople, S., Wutschitz, L., Zanella-Béguelin, S. (2025). Securing AI Agents with Information-Flow Control. arXiv:2505.23643.
5. Debenedetti, E., Shumailov, I., Fan, T., Hayes, J., Carlini, N., Fabian, D., Kern, C., Shi, C., Terzis, A., Tramèr, F. (2025). Defeating Prompt Injections by Design. arXiv:2503.18813.
6. Greenblatt, R., Shlegeris, B., Sachan, K., Roger, F. (2024). AI Control: Improving Safety Despite Intentional Subversion. ICML. arXiv:2312.06942.
7. Hills, J., Caspary, I., Cooper Stickland, A. (2026). Distributed Attacks in Persistent-State AI Control. arXiv:2607.02514.
8. Kothamasu, V., Smith, V., Yadav, C. (2026). Hidden in Plain Sight: Benchmarking Agent Safety Against Decomposition Attacks with DECOMPBENCH. arXiv:2606.13994.
9. Kravchenko, A., Liventsev, V., Konstantinov, I., Iskhakov, I., Kukuy, M. (2026). APPA: Recoverable Information-Flow Control for Real-World LLM Agents. arXiv:2607.24625.
10. Makins, O., Angelini, O., Shams, Z., Phuong, M. (2026). Multi-Agent AI Control: Distributed Attacks Hamper Per-Instance Monitors. arXiv:2607.07368.
11. METR (2026). Brief independent investigation of agents' behavior, reasoning and collaboration in the OpenAI / Hugging Face hacking incident. https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/
12. Remedios, A., Storf, S., Roger, F., Hughes, J. (2026). Red-Teaming Auto Mode: Improving Blocking Classifiers Against Malign Coding Agents. arXiv:2609.19587.
13. Rose, A., Cullen, C., Abdelnabi, S., Torr, P., Kaplowitz, B. G., Schroeder de Witt, C. (2026). Detecting Multi-Agent Collusion Through Multi-Agent Interpretability. arXiv:2604.01151.
14. Sun, B., Zhao, Z., Liu, X., Cao, Y., Xiao, C. (2026). Decomposition Attacks Across Unlinkable Identities: Limits of Stateful Defenses for LLM Services. arXiv:2608.17445.
15. Swarm Traces (2026). Revealing the details of how OpenAI agents hacked Hugging Face. https://swarmtraces.org/
16. Wang, Y., Yan, Z., Zhang, J., Wu, Z., Zheng, M., Sun, Z., Zhu, Y., Cai, T. (2026a). MAP-Graph: Provenance-Aware Shared Memory for Multi-Agent Workflows. arXiv:2608.10509.
17. Wang, Y., Zhang, J., Wu, Z., Cai, T., et al. (2026b). From Agent Traces to Trust: A Survey of Evidence Tracing and Execution Provenance in LLM Agents. arXiv:2606.04990.

---

## Appendix A. Details  *(not counted in the page limit)*

- A.1 Judge prompt (verbatim from `src/swarm_oversight/judge.py`) and worker system prompt (`agents/worker.py`).
- A.2 Task families: the three pieces of each, and the completion checks (as in §3).
- A.3 Benign templates: the 15 template names with one-line descriptions (`tasks/benign/templates.py`).
- A.4 Frozen parameters (`configs/frozen.yaml`) and the development-tuning table: clustering θ ∈ {0.70…0.95} and
  provenance h ∈ {1, 2, 3}, with grouping recall and benign group size.
- A.5 Per-family results and the full q sweep [[from summary.md]].
- A.6 Changes from the pre-sprint plan, so judges see a transparent process (shortened list from PROJECT.md §8).

## Appendix B. Limitations and Dual-Use / Ethical Considerations  *(required)*

**What the results establish, and what they do not.** They establish how much of joint review's safety each grouping
rule recovers in a mock store, for one pair of models, three proxy sabotage families and scripted attacks, at matched
audit budgets. They do not establish detection rates for real swarms, real harms or adaptive attackers. They also say
nothing about channels the harness does not log.

**Dual-use risk.** The two evasion strategies show how a split attack can slip past a given grouping rule: disguising
names and wording, and routing hand-offs through busy shared files. This could help someone make multi-agent
operations harder to detect. Both strategies either already appear in public red-teaming work (renaming and
rewording, Brown et al., 2026) or follow directly from the rules' definitions. We report them as measurements that
tell defenders which logs and rules to rely on.

**Mitigations.**
- Proxy goals only: fake keys, a 60-row toy dataset, mock configs, test-range IP addresses, and no network access.
- No real system was touched.
- Attack strategies are described only at the strategy level in this report, and the attack templates sit in one
  clearly labelled file. [[Repository private until judging, if chosen.]]
- No real swarm data was used.

**Benefit.** The results tell deployers which grouping signal to collect, namely harness read/write logs, before larger
swarms are deployed, and where the remaining risk lies (grouping versus judging).

## LLM Usage Statement

[[Edit to match what you actually did.]] We used Claude (Anthropic) as a coding assistant to implement the harness and
analysis code, run experiments, and draft text for sections of this report, which we then rewrote. The authors chose
and verified every design decision, result and claim. We opened and checked every reference, and all reported numbers
come from the released code and logs.
