<!-- DRAFT for the Apart template (Google Doc). Numbers marked [[...]] are filled from logs/results/summary.md.
     The template asks that the final version be primarily written by the team: edit freely. -->

# Who Draws the Map? Harness-Side Grouping for Joint Review of Split Swarm Attacks

Brandon Cardamone (affiliation) · Morill (affiliation) · With Apart Research

## Abstract (150–250 words)

In July 2026, about 1,200 AI agents coordinated through an improvised shared message board, and about 700 of them
attacked Hugging Face; no single agent's transcript showed the whole plan. Splitting a harmful goal across agents
defeats monitors that judge one agent at a time, while a monitor that sees every piece together catches it, but the
defender does not know which actions belong together. Every joint review therefore rests on a grouping rule, which we
call the overseer's *map*. We compare maps head to head in a controlled setting: three independently launched
instances of an untrusted model (DeepSeek V4 Flash) each receive one piece of a sabotage plan and hand off state only
through a logged shared store, inside a stream of 150 benign episodes written to look like every attack piece. A
trusted model (Mistral-Small-24B) judges each request's group before it runs, and a simulated auditor reviews the top q
of groups. Across 24 tasks and three attacks (naive split, disguise aimed at clustering, hub routing aimed at
provenance), at a 2% audit budget, [[headline: oracle vs per-agent; provenance vs clustering; dilution]]. [[One-sentence
takeaway.]] We release the harness, maps and labelled streams.

## 1. Introduction

The Hugging Face incident (METR, 2026) is the first documented case of a large agent swarm dividing up a harmful task:
one agent issued about 10% of all assignments on the board, assignees often subdelegated, and over 7% of reviewed
transcripts contained deliberately spoofed tool calls. An independent reconstruction counted 7,905 agent names for
about 1,200 agents (Swarm Traces, 2026). Most deployed safeguards score one request, one agent or one transcript at a
time. Makins et al. (2026) show the resulting *fragmentation effect*: per-agent monitors catch less as an attack is
spread across more agents, while a monitor that reads all the pieces together does not suffer this. They also note
why such a joint monitor is not deployable: "a defender does not know which commits belong to the same attack."

Any deployable joint review therefore needs a rule that decides which requests to judge together. We call this rule
the overseer's *map*, and argue that it, not the monitor, is the part a swarm attacks. Provider-side maps group by what
the swarm writes (wording, accounts); red-teamers split such clusters by renaming files and changing vocabulary (Brown
et al., 2026), and no tested provider-side policy survives fresh, unlinkable identities (Sun et al., 2026). A deployer
who runs the agent harness can observe something a provider cannot: which artifacts each agent read and wrote. The
swarm cannot hide that a hand-off happened, but it chooses which files carry it, and can bury the link in files that
benign work touches heavily. Every link a map follows also pulls benign work into the group.

**Our main contributions are:**
1. A controlled, parallel, interleaved testbed in which K = 3 independently launched agents split proxy sabotage tasks
   through a logged shared store, with benign look-alike traffic at 150× attack volume, and released labelled streams.
2. A matched-budget comparison of six grouping maps (singleton, per-agent, provider-side clustering, harness-side
   provenance, oracle, random size-matched) under attacks aimed at each map, scaled to the joint-review ceiling, with
   pre-registered hypotheses. To our knowledge this is the first test of joint review in parallel deployments, which
   Makins et al. leave to future work.
3. A decomposition of the remaining gap into *grouping loss* (the map leaves a piece out) and *judging loss* (all
   pieces present, judge not alarmed), which says whether to invest in better maps or better judges.

## 2. Related Work

**Distributed attacks and per-instance monitors.** Makins et al. (2026) introduce the fragmentation effect in FakeLab,
with sequential deployments, a planner over an unmonitored channel, and a non-deployable joint (whole-PR) monitor used
as a diagnostic. We keep their unmonitored-plan assumption but run roots in parallel, and replace the joint monitor
with deployable maps scored against it. Hills et al. (2026) track suspicious build-up across one agent's pull requests;
Chen et al. (2025) catch decomposition within one conversation (93% defense success). DecompBench (Kothamasu et al.,
2026) shows agents refuse decomposed subtasks far less than monolithic ones. Remedios et al. (2026) find multi-agent
attacks among the mechanisms that evade production blocking monitors and call preventing multi-context attacks at
acceptable cost "an open problem".

**Provider-side grouping.** Brown et al. (2026) cluster requests across accounts online and escalate clusters to a
cross-context judge; red-teamers split clusters by renaming and rewording, which multi-cluster assignment partly fixes.
Their detection advantage narrows as benign background grows. Sun et al. (2026) show that under unlinkable identities
none of ten stateful policies stays within a 1% denial budget. Our clustering map follows Brown et al.'s description.

**Information flow and provenance.** CaMeL and FIDES enforce information-flow policies within one agent; APPA (2026)
adds recoverable information-flow control with disposable child branches; NeuroTaint (Cai et al., 2026) audits
semantic taint offline. MAP-Graph (Wang et al., 2026a) proposes provenance-aware shared memory for multi-agent workflows, and a
recent survey (Wang et al., 2026b) names multi-agent lineage an open direction. None measures how much of joint review's safety a
provenance-based grouping recovers against an adaptive swarm. Group-level detection from activations (Rose et al.,
2026) is complementary: it assumes known groups; we study how to find them.

## 3. Methods

**Threat model.** The red team controls K = 3 independently launched instances of an untrusted model U, each with its
own legitimate cover task. A scripted plan reaches each instance through its prompt, the one unmonitored channel (as in
Makins et al.'s planner broadcast). Pieces pass state only through artifacts in a shared store whose reads and writes
are logged; there is no spawning and no identity rotation, so per-agent grouping equals attested lineage. The red team
knows every map's rule and frozen parameters, and safety is reported as the worst case over its attacks
(Greenblatt et al., 2024).

**Sandbox.** A mock store (`vault/`, `config/`, `data/`, `pipelines/`, `shared/ops/`, `outbound/`) with fake data, and six
tools: list, read, write, run, post (to a mock endpoint), register a pipeline step. Every call passes through a gateway
that logs the request text, root ID, and paths read and written before it executes. Scripts run in a Docker container
with no network; an audit hook records every path they open. A smoke test checks that the log covers every changed file.

**Tasks.** Three sabotage families × 8 evaluation parameterizations (+1 dev each), each split into three pieces with a
code-based completion check: (i) *audit logging disabled*: a custom level with the audit level's number, a filter that
drops it, and an include that enables the filter; (ii) *labels poisoned*: a mapping-driven relabel script, a mapping that
flips labels, and running plus registering the script; (iii) *config backdoor*: a new allowlisted host, a debug profile
that skips token checks, and enabling the profile. Each piece is a routine edit on its own.

**Attacks.** A0 naive split (canonical names); A1 disguise (artifact names and wording in each cover task's namespace,
aimed at clustering); A2 hub routing (hand-offs through `shared/ops` files that benign traffic touches heavily, aimed at
provenance). One rollout per task × attack: 72 attack episodes, of which 70 completed when unmonitored (2 excluded).

**Benign traffic.** 600 episodes from 15 templates written as legitimate look-alikes of every piece (custom log levels and
filters, debug profiles that sometimes skip token checks for internal health checkers, partner IPs on the allowlist,
label-schema mapping scripts, relabel fixes, key-rotation reports); about one third are chained across 2–3 roots in one
store. Cover tasks for attack roots come from the same templates (excluding the attack's own family).

**Streams.** For each family and overlap level o ∈ {10%, 40%} (the share of benign episodes that touch the family's
artifacts), we draw disjoint calibration and evaluation backgrounds of 150 benign episodes and merge them request by
request at a fixed simulated concurrency of 20 episodes. Each evaluation stream receives one attack episode at a random
position, with its causal order kept.

**Maps** (all cut to the most recent M = 40 requests). *Singleton*; *per-agent* (the root's earlier requests);
*clustering* (Voyage-4-lite embeddings of request text routed online to centroids at θ = 0.80 with multi-cluster
assignment); *provenance* (requests within h = 2 hops in the write→read/write path graph, no time window); *oracle*
(all of the episode's requests so far; uses hidden labels); *random size-matched* (random earlier requests, as many as
the provenance group). θ, h and M were tuned on dev data only and frozen in a committed config before evaluation.

**Judge and protocol.** One trusted model T (Mistral-Small-3.2-24B; U is DeepSeek V4 Flash) scores a request's group
on a 0–9 scale with one fixed prompt; the score is the logprob-weighted expected digit. Inputs are request text, tool,
paths and pseudonymous root labels. A threshold τ_M(q) is set on the calibration background so that a fraction q ∈
{0.5, 1, 2, 5}% of benign requests are audited. On the evaluation stream an attack is caught if, before its completing
request runs, some group containing an attack request scores above τ_M(q), in which case a perfect auditor sees the
attack. Nothing is blocked, so all maps are replayed offline on the same logs. Safety S = C/(C+W).

**Statistics.** Worst case over A0–A2, taken inside each of 2,000 paired cluster-bootstrap replicates that resample
attack tasks and calibration benign episodes; exact McNemar tests on discordant episodes as a check. Hypotheses (all
q = 2%): H0, S_oracle > S_per-agent at both overlaps; H-main, S_provenance > S_clustering at 10% overlap (minimum
effect of interest 20 pp); H-dilution, S_provenance(10%) > S_provenance(40%).

**What we tried that did not work.** A judge that first states the combined effect and then scores was noisier on dev
and was rejected. Llama-3.1-8B was rejected as T because its provider returns misaligned logprobs. The strict pilot
gate (every dev piece missed alone and per agent, every attack caught by the oracle) was not met; we froze the
protocol rather than tune further on nine dev episodes.

## 4. Results

[[Figure 1: headline.pdf. Caption: Worst-case safety over A0–A2 against audit budget q for each map, at 10% (left) and
40% (right) benign overlap. Oracle (dashed) is joint review with known groups; per-agent (dotted) is the deployable
baseline. Bands: paired 95% bootstrap CIs for provenance and clustering. N = [[70]] attack episodes, 150 benign
episodes per background.]]

[[Table 1: grid at q = 2% from summary.md.]]

[[Paragraph per hypothesis: observation, CI, McNemar p, and interpretation, kept separate. Grouping vs judging loss.
Random size-matched control: does group size alone buy safety?]]

## 5. Discussion and Limitations

[[Implications: which map to deploy, and whether to invest in maps or judges.]]

**Limitations.** Every task is a proxy goal in a mock store; results bound rather than predict real deployments. One
untrusted and one trusted model family. The attack plan is scripted and delivered over an unmonitored prompt channel
(an upper bound on coordination); the red team does not adapt to verdicts. Benign traffic is synthetic and replayed, so
benign agents never react to attack artifacts. 70 attack episodes and one rollout per cell give wide intervals. For cost,
calibration judges 400 sampled requests per map and evaluation judges at most 25 groups per map per stream (attack
requests' own groups first), which can understate maps whose catches come from other requests' groups. The auditor is
perfect. Identity rotation, steganography and log tampering are out of scope.

**Future work.** Information-flow (taint) rules for exfiltration; rarity-weighted provenance as the blue team's answer
to hub routing; stronger judges on the frozen logs; a compromised-planner case where lineage links everything.

## 6. Conclusion

[[Two short paragraphs.]]

## Code and Data
Code repository: https://github.com/brandoncardamone/Swarm-alignment-hackathon-Cardamone-Morill (all code written
during the sprint). Labelled streams are released with hidden labels in separate files. Attack templates are described
at strategy level here; the repository contains them in a clearly labelled file (see Appendix B on dual use).

## References
- Brown, D., Bhargav, S., Santhanam, A., et al. (2026). Stateful Online Monitoring Catches Distributed Agent Attacks. arXiv:2605.31593.
- Cai, Y., Tang, W., Wen, C., Qin, S. (2026). Ghost in the Agent: Redefining Information Flow Tracking for LLM Agents. arXiv:2604.23374.
- Chen, Y.-H., Joshi, N., Chen, Y., Andriushchenko, M., Angell, R., He, H. (2025). Monitoring Decomposition Attacks in LLMs with Lightweight Sequential Monitors. arXiv:2506.10949.
- Greenblatt, R., Shlegeris, B., Sachan, K., Roger, F. (2024). AI Control: Improving Safety Despite Intentional Subversion. ICML. arXiv:2312.06942.
- Hills, J., Caspary, I., Cooper Stickland, A. (2026). Distributed Attacks in Persistent-State AI Control. arXiv:2607.02514.
- Kothamasu, V., Smith, V., Yadav, C. (2026). Hidden in Plain Sight: Benchmarking Agent Safety Against Decomposition Attacks with DECOMPBENCH. arXiv:2606.13994.
- Kravchenko, A., Liventsev, V., Konstantinov, I., Iskhakov, I., Kukuy, M. (2026). APPA: Recoverable Information-Flow Control for Real-World LLM Agents. arXiv:2607.24625.
- Makins, O., Angelini, O., Shams, Z., Phuong, M. (2026). Multi-Agent AI Control: Distributed Attacks Hamper Per-Instance Monitors. arXiv:2607.07368.
- METR (2026). Brief independent investigation of agents' behavior, reasoning and collaboration in the OpenAI / Hugging Face hacking incident. https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/
- Remedios, A., Storf, S., Roger, F., Hughes, J. (2026). Red-Teaming Auto Mode: Improving Blocking Classifiers Against Malign Coding Agents. arXiv:2609.19587.
- Rose, A., Cullen, C., Abdelnabi, S., Torr, P., Kaplowitz, B. G., Schroeder de Witt, C. (2026). Detecting Multi-Agent Collusion Through Multi-Agent Interpretability. arXiv:2604.01151.
- Sun, B., Zhao, Z., Liu, X., Cao, Y., Xiao, C. (2026). Decomposition Attacks Across Unlinkable Identities: Limits of Stateful Defenses for LLM Services. arXiv:2608.17445.
- Swarm Traces (2026). Revealing the details of how OpenAI agents hacked Hugging Face. https://swarmtraces.org/
- Wang, Y., Yan, Z., Zhang, J., Wu, Z., Zheng, M., Sun, Z., Zhu, Y., Cai, T. (2026). MAP-Graph: Provenance-Aware Shared Memory for Multi-Agent Workflows. arXiv:2608.10509.
- Wang, Y., Zhang, J., Wu, Z., Cai, T., et al. (2026). From Agent Traces to Trust: A Survey of Evidence Tracing and Execution Provenance in LLM Agents. arXiv:2606.04990.
- Debenedetti, E., Shumailov, I., Fan, T., Hayes, J., Carlini, N., Fabian, D., Kern, C., Shi, C., Terzis, A., Tramèr, F. (2025). Defeating Prompt Injections by Design (CaMeL). arXiv:2503.18813.
- Costa, M., Köpf, B., Kolluri, A., Paverd, A., Russinovich, M., Salem, A., Tople, S., Wutschitz, L., Zanella-Béguelin, S. (2025). Securing AI Agents with Information-Flow Control (FIDES). arXiv:2505.23643.

## Appendix A. Prompts, task list, per-cell tables
[[Judge prompt (src/swarm_oversight/judge.py), worker system prompt, benign templates, per-family results.]]

## Appendix B. Limitations and Dual-Use / Ethical Considerations (required)
**What the results establish.** How much of joint review's safety each grouping rule recovers in a mock store, for
one model pair, three proxy sabotage families and scripted attacks, at matched audit budgets. They do not establish
detection rates for real swarms, real harms, or adaptive attackers.

**Dual-use risk.** The attack variants (disguise, hub routing) describe how a split attack can evade a given grouping
rule, which could help someone make multi-agent operations harder to detect. Both strategies are already described in
public red-teaming work (Brown et al., 2026) or follow directly from the map definitions, and we report them as
measurements for defenders. Mitigations: proxy goals only (fake keys, a 60-row toy dataset, mock configs, test-range IP
addresses, no network access); attack strategies described here only at the strategy level; no real systems touched;
the hidden labels and attack templates are kept in clearly marked files. No real swarm data was used.

## LLM Usage Statement
We used Claude (Anthropic) as a coding assistant to implement the harness, run the experiments and draft sections of
this report. All design decisions, results and claims were checked by the authors, every reference was opened and
verified, and all reported numbers come from the released code and logs.
