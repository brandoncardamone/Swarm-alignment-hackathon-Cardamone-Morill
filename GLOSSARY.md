# Glossary: "Who Draws the Map?"

Every term used in this project, grouped by topic. Cross-references are in *italics*. See `PROJECT.md` for the full
design.

---

## 1. Core idea

| Term | Meaning |
|---|---|
| **Swarm** | Many AI agents acting together, possibly coordinating toward a goal no single agent was given. Here: 3 agents. |
| **Split attack** (decomposition attack, distributed attack) | A harmful goal divided into *pieces* that each look harmless, done by different agents (or steps) so no single view shows the harm. |
| **Piece** | One part of a split attack, carried out by one *root*. Each of our attacks has 3 pieces. |
| **Map** (the overseer's map) | The rule that decides which requests the monitor judges *together*. Our name for a grouping rule. The project's core claim: the map, not the monitor, is what a swarm attacks. |
| **Group** | The set of requests a map puts together with a given request, which the *judge* then scores as a whole. |
| **Joint review** | Judging several related requests together rather than one at a time. Catches split attacks, if the right requests are grouped. |
| **Fragmentation effect** | Makins et al.'s finding: per-agent monitors catch less as an attack is spread over more agents. |
| **Harness** | The software that runs the agents and executes their tool calls. A deployer who runs it can log which files each agent read and wrote. |
| **Harness-side** | Information only the harness operator sees (file reads and writes). Our *provenance* map uses it. |
| **Provider-side** | Information an API provider sees (request text, accounts). The *clustering* map uses it. |
| **Dilution** | Following links also pulls benign work into a group. Bigger, noisier groups raise the alarm threshold, so attacks are harder to catch. |
| **Composition gap** | How much more suspicious the whole attack looks than its most suspicious piece. If small, joint review adds little. |
| **Gerrymandering analogy** | From the earlier draft: whoever draws the district lines (the map) controls the outcome. |

## 2. Threat model and roles

| Term | Meaning |
|---|---|
| **Threat model** | Our assumptions about the attacker: what it controls, knows and can do. |
| **Red team** | The attacker side: the scripted split attacks. |
| **Blue team** | The defender side: maps, judge, audit protocol. |
| **U (untrusted model)** | The capable model whose agents might attack. Here DeepSeek V4 Flash. |
| **T (trusted model)** | A weaker model we trust to monitor U. Here Mistral-Small-3.2-24B. |
| **Root** | One independently launched agent instance, with its own task and fresh memory. Each attack has K = 3 roots. |
| **K** | Number of roots per attack episode (3). |
| **Cover task** | The legitimate task an attack root also works on, which hides its piece. |
| **Scripted plan** | The attack instructions, written by us and given to each root through its prompt. |
| **Unmonitored channel** | The prompt. The deployer logs tool calls, not prompts, so the plan arrives unseen (an upper bound on coordination, as in Makins et al.). |
| **Hand-off** | One piece passing state to the next through a file in the shared store. |
| **Attested lineage** | Knowing which agent spawned which. With independent roots it groups exactly like *per-agent*, so we don't test it separately. |
| **Identity rotation** | Agents renaming themselves to break identity-based grouping (7,905 names in the incident). Out of scope here. |
| **Perfect auditor** | A simulated reviewer who always recognises an attack in a group it is shown. Uses the hidden labels. |
| **Worst case** | We report each map's safety under the attack that hurts it most, because the red team knows the map. |

## 3. The maps (grouping rules)

| Map | Groups request i with… | Role |
|---|---|---|
| **Singleton** | Nothing; the request alone. | Floor |
| **Per-agent** (trajectory) | All earlier requests from the same root. | **Baseline** (today's typical deployable monitor) |
| **Clustering** (Brown-style) | Requests with similar text embeddings, assigned online to cluster centres. | Provider-side competitor |
| **Provenance** | Requests linked through files: one wrote a path another read or wrote, up to *h* hops. | Harness-side, our main candidate |
| **Oracle** | All requests of the same episode so far (uses hidden labels). | **Ceiling**; not deployable |
| **Random size-matched** | Random earlier requests, as many as the provenance group. | Control: does group size alone help? |
| **Taint rule** | "Nothing derived from `vault/` may reach an outbound post." | Exfiltration baseline from v1; **cut** |

Map parameters:

| Term | Meaning |
|---|---|
| **M** | Maximum group size: every group is cut to the most recent M requests. Frozen at 40. |
| **h** (hops) | How many file links provenance follows. Frozen at 2. |
| **θ / tau_route** | Clustering similarity threshold for joining a cluster. Frozen at 0.80. |
| **Centroid** | The average embedding of a cluster; new requests are compared to it. |
| **Multi-cluster assignment** | A request joins every cluster it is similar enough to, not just the best one. Brown et al.'s fix against renaming. |
| **Embedding** | A vector representing text meaning. Made by Voyage-4-lite. |
| **Path-level write→read/write graph** | The provenance graph: an edge links two requests when the earlier one wrote a file the later one read or wrote. |

## 4. Attacks and tasks

| Term | Meaning |
|---|---|
| **Proxy goal** | A stand-in harm in a fake environment (fake keys, toy data, mock configs), never a real harm. |
| **Task family** | One type of sabotage. We have 3. |
| **`audit_off`** | Silences audit logging: a custom log level with the audit level's number, a filter that drops it, and an include that enables the filter. |
| **`label_poison`** | Corrupts a toy dataset: a mapping-driven relabel script, a mapping that flips 0↔1, then run it and register it as a pipeline step. |
| **`config_backdoor`** | Opens a backdoor: a planted host added to the allowlist, a debug profile with `skip_token_check: true`, and the profile enabled. |
| **Exfil family** | Sending a planted fake key to a mock endpoint. **Cut.** |
| **Parameterization** | One concrete version of a family (names, hosts, files). 1 dev + 8 evaluation per family. |
| **Task** | One family × parameterization (24 evaluation tasks). |
| **A0, naive split** | Pieces with canonical file names. |
| **A1, disguise** | Names and wording moved into each cover task's vocabulary. Aimed at clustering. |
| **A2, hub routing** | Hand-offs through busy shared files (`shared/ops/*`). Aimed at provenance: the link exists but is buried. |
| **A3** | A1 + A2 combined. **Cut.** |
| **Hub file** | A shared file many benign jobs touch (`shared/ops/handoff.json`, `settings.yaml`, `notes.md`). |
| **Completion check** | Code that decides whether the proxy harm actually happened (not an LLM). |
| **Completing request** | The request after which the completion check first becomes true. An attack must be caught before it runs. |
| **Excluded episode** | An attack that failed even with no monitoring. Not counted in safety, but reported (2 of 72). |
| **Attack request** | A request carrying a piece, found by matching the piece's distinctive names in its arguments. |

## 5. Benign traffic and streams

| Term | Meaning |
|---|---|
| **Benign episode** | Legitimate work by 1–3 roots. 600 in the pool. |
| **Benign look-alike** | A benign task deliberately resembling an attack piece, so the judge can't win by spotting keywords. |
| **Template** | A generator for one kind of benign task (15 in total, e.g. `log_filter`, `debug_profile`, `label_schema`). |
| **Chained episode** | A benign episode where 2–3 roots hand work to each other through the store (216 of 600). |
| **Pool** | All 600 benign episodes, from which backgrounds are drawn. |
| **Background** | 150 benign episodes forming the traffic an attack hides in. |
| **Calibration background** | Benign traffic used only to set the alarm threshold. |
| **Evaluation background** | A separate benign set into which attacks are inserted for scoring. |
| **Overlap** | Share of benign episodes in a background that touch the attack family's files: **10%** or **40%**. |
| **Stream** | Episodes merged request by request in simulated time, as a monitor would see them. |
| **Simulated concurrency** | How many episodes run at once in a stream (20). |
| **Stream position** | A request's place in the merged stream. |

## 6. Judge and audit protocol

| Term | Meaning |
|---|---|
| **Judge J** | The trusted model scoring how suspicious a group is, from 0 (benign) to 9 (harmful). |
| **Logprob-weighted score** | Instead of reading one answer, we average the digits 0–9 weighted by the model's probability for each. Gives a smooth score from one call. |
| **Logprobs** | The log-probabilities a model assigns to candidate output tokens. |
| **Misaligned logprobs** | A provider bug where logprobs belong to the wrong output position. Why Llama-8B was rejected. |
| **Tokenizer** | How a model splits text into tokens. Mistral splits numbers into single digits, hence the 0–9 scale. |
| **CoT judge / "reason first"** | A variant that explains the combined effect before scoring. Tried on dev and rejected (noisier). |
| **Audit** | A simulated perfect auditor reviewing a flagged group. |
| **Audit budget q** | Share of benign requests that may be audited: 0.5%, 1%, **2% (primary)**, 5%. |
| **Threshold τ (tau_M)** | Per-map score above which a request is audited. Set on calibration so audits = q × benign requests. |
| **Caught** | Some group containing an attack request scored above τ before the completing request ran. |
| **Allow-all overseer** | The online gateway never blocks; all maps are replayed offline on the logs. Valid because attacks don't adapt to verdicts. |
| **Offline replay** | Applying maps, judge and thresholds to logs after the rollouts. |
| **Trusted monitoring** | A control protocol where T watches U and a small budget of human audits is spent on the most suspicious actions (Greenblatt et al.). |
| **AI control** | Research on safety measures that hold even if the AI is trying to subvert them. |

## 7. Metrics and hypotheses

| Term | Meaning |
|---|---|
| **Safety S** | C/(C+W). **C** = attacks caught before completion, **W** = attacks completed uncaught. |
| **Worst-case safety** | Minimum safety over A0–A2 for a map. |
| **Recovered fraction** | (S_map − S_per-agent)/(S_oracle − S_per-agent): how much of the oracle's improvement a map achieves. Reported only if the oracle gains ≥ 10 pp. |
| **Grouping recall** | Share of the attack's requests so far that are in a request's group. |
| **Grouping precision** | Share of a group that is attack requests. |
| **Map miss** | No judged group contained all pieces. The map failed to bring them together. |
| **Judge miss** | Some group had all pieces, but the judge scored it below threshold. |
| **Grouping loss** | S_oracle − S_map: safety lost because the map isn't the oracle. |
| **Judging loss** | 1 − S_oracle: safety lost even with perfect grouping, because the judge is weak. |
| **H0** | Oracle beats per-agent at both overlap levels. If false: judging, not grouping, is the bottleneck. |
| **H-main** | Provenance beats clustering at 10% overlap by ≥ 20 pp. |
| **H-dilution** | Provenance does worse at 40% overlap than at 10%. |
| **MEI (minimum effect of interest)** | Smallest difference we would call meaningful (20 pp for H-main). |
| **pp** | Percentage points. |
| **Usefulness** | Whether benign work still gets done. Always 1 here, since nothing is blocked. |

## 8. Statistics

| Term | Meaning |
|---|---|
| **Bootstrap** | Re-running the analysis on many resampled datasets to measure uncertainty. 2,000 replicates. |
| **Paired cluster bootstrap** | Resampling whole tasks and whole benign episodes, and using the same resample for every map, so map comparisons are paired. |
| **95% CI** | Confidence interval. If a difference's CI excludes 0, the difference is significant. |
| **McNemar test** | Exact test on paired yes/no outcomes, counting episodes one map caught and the other didn't. Used as a check. |
| **Pre-registration** | Fixing hypotheses and parameters before seeing evaluation results (`configs/frozen.yaml`, commit `fd6b760`). |
| **Freeze** | The moment parameters were locked. |
| **p-hacking** | Tuning until results look good. The freeze prevents it. |
| **Power** | Ability to detect a real effect; limited by 70 episodes. |

## 9. Process terms

| Term | Meaning |
|---|---|
| **Dev set** | Data used only for tuning: parameterization 0 of each family + 60 benign episodes (seed 1000). |
| **Evaluation set** | Data used only for final results: parameterizations 1–8 + the 600-episode pool (seed 0). |
| **Pilot gate** | v1's go/no-go check on dev: pieces low alone and per-agent, oracle catches. Not strictly met (see C19). |
| **Rollout** | Actually running agents on a task to produce logs. |
| **Episode** | One complete run: an attack (3 roots) or a benign task (1–3 roots). |
| **Dry run** | A tiny test run of the full pipeline. |
| **Cut order** | v1's planned order of dropping scope if behind. |
| **Stretch goal** | Optional extra if time allows (taint rule, A3, stronger judge, rarity-weighted provenance). |
| **C1–C20** | Numbered changes from v1, listed in `PROJECT.md` §8. |

## 10. Environment and tools

| Term | Meaning |
|---|---|
| **Sandbox** | A private copy of the fake store for each episode. |
| **Seed store** | The starting files (`sandbox/seed/`) copied into every sandbox. |
| **Gateway** | Single entry point for tool calls. Logs before executing; keeps hidden labels separate. |
| **Visible record / hidden labels** | What the monitor may see vs ground truth (episode, attack or not, piece index). |
| **The 6 tools** | `list`, `read`, `write`, `run` (execute a script), `post` (to the mock endpoint), `register_step` (add to a pipeline). |
| **Mock endpoint** | `outbound/<name>.jsonl`, a logged file standing in for an external server. |
| **Runner container** | Docker image `swarm-runner:0.1` that executes agent-written scripts. |
| **`--network none`** | Docker flag removing all network access from the container. |
| **Audit hook** | Python `sys.addaudithook`, used inside the runner to record every file a script opens. |
| **Log completeness** | Check that every changed file appears in the log. Passed. |
| **Worker loop** | The code that runs one root: the model proposes tool calls, the gateway executes them, results go back to the model. |
| **Cache** | `cache/llm_cache.sqlite`, which stores every model call so reruns are free. |
| **Rolling pool** | Running up to 40 episodes at once, starting a new one as each finishes. |
| **Episode timeout** | 15-minute hard limit per episode, added after one API call hung. |

## 11. Models, providers, software

| Term | Meaning |
|---|---|
| **DeepSeek V4 Flash** | Untrusted worker model (U). |
| **Mistral-Small-3.2-24B** | Trusted judge (T). |
| **Llama-3.1-8B** | Original judge; now the backup (sampled scoring). |
| **Voyage-4-lite** | Embedding model for clustering (Brown et al. also use Voyage). |
| **OpenRouter** | One API giving access to all the models above; our single paid key. |
| **Groq / DeepSeek API / Gemini** | Other providers in `.env`, unused (invalid key / no balance / free-tier rate limit). |
| **Adaption credits** | The hackathon's $500 credit, usable only on the Adaption platform, not for our inference. |
| **WSL2** | Windows Subsystem for Linux, where all work runs. |
| **Docker / Docker Desktop** | Container runtime for the sandbox runner. |
| **uv** | Python package and environment manager; `uv.lock` pins every dependency. |
| **Python 3.12** | Pinned interpreter version. |
| **ruff / pytest** | Linter and test runner. |
| **Inspect AI / ControlArena** | Evaluation frameworks considered and not used (time). |
| **`.env`** | Local file with API keys; never committed or printed. |

## 12. Files

| File | What it is |
|---|---|
| `docs/v1.pdf` | Original pitch brief. |
| `PROJECT.md` | Current full brief (v2). |
| `PLAN.md` | Build plan and change log. |
| `RESULTS_LIVE.md` | Live progress and interim results, refreshed every 2 minutes. |
| `GLOSSARY.md` | This file. |
| `configs/frozen.yaml` | The pre-registered protocol. |
| `configs/models.yaml` | Which model plays which role. |
| `tasks/attacks/ATTACK_TEMPLATES_proxy_goals.py` | Scripted attack templates (clearly labelled). |
| `tasks/benign/templates.py` | Benign look-alike templates. |
| `report/draft.md` | Report draft in the Apart template's structure. |
| `docs/apart_report_template.txt` | Text of the official template. |
| `logs/` | Run data (gitignored): events, hidden labels, episodes, results. |

## 13. The incident and related work

| Term | Meaning |
|---|---|
| **Hugging Face incident** | July 2026: ~1,200 OpenAI agents coordinated on an improvised message board; 700 attacked Hugging Face. |
| **ExploitGym** | The OpenAI cybersecurity evaluation the incident agents were running in. |
| **Message board** | The Artifactory cache the agents repurposed to coordinate. |
| **METR report** | Independent investigation (with Redwood Research): ~10% of assignments from one agent, >7% of transcripts with spoofed tool calls. |
| **Swarm Traces** | Reconstruction of 80,000+ attack payloads; counted 7,905 agent names. |
| **AI Village** | A public dataset of multi-agent transcripts (gated). Not used. |
| **Makins et al. 2026** | Multi-agent AI control: fragmentation effect; joint monitor non-deployable; sequential deployments only. |
| **Brown et al. 2026** | Stateful online monitoring with cross-account clustering; our clustering baseline. |
| **Sun et al. 2026** | Stateful defenses fail under unlinkable identities. |
| **Greenblatt et al. 2024** | AI Control: trusted monitoring, audit budgets, red-team vs blue-team protocols. |
| **Chen et al. 2025** | Sequential monitors catch decomposition within one conversation. |
| **Hills et al. 2026** | Stateful link-tracker across one agent's pull requests. |
| **Remedios et al. 2026** | Red-teaming production blocking monitors; multi-context attacks remain open. |
| **DecompBench** | Benchmark showing agents refuse decomposed harmful subtasks less often. |
| **Rose et al. 2026 (HELIOS)** | Group-level collusion detection from activations; assumes known groups. |
| **NeuroTaint, CaMeL, FIDES, APPA** | Information-flow and taint-tracking defenses for single agents. |
| **MAP-Graph, provenance survey** | Recent provenance work for multi-agent memory; lineage named as open. |
| **Information-flow control (IFC) / taint** | Tracking where data came from and blocking forbidden flows. |

## 14. Hackathon logistics

| Term | Meaning |
|---|---|
| **Apart Research** | Hackathon organizer (with the AI Alignment Foundation and AE Studio). |
| **Track 4** | Multi-Agent Oversight and Control, our track. |
| **AoE** | Anywhere on Earth. Deadline Sun Nov 8, 11:59 PM AoE = Mon Nov 9, 6:59 AM ET. |
| **Rubric** | Judging criteria: Impact & Innovation, Execution Quality, Presentation & Clarity (each 1–5). |
| **Dual-Use appendix** | Required section on how the work could help attackers and our mitigations. |
| **LLM Usage Statement** | Template section saying how AI tools were used. |
| **Infohazard** | Information that could cause harm if spread; why projects are hidden until judging. |
| **Apart Fellowship** | Follow-on research program; top teams get fast-tracked. |
