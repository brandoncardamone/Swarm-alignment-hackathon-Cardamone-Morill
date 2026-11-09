# Who Draws the Map? Harness-side grouping for joint review of split swarm attacks

Apart Research **Swarm Alignment Hackathon** (Nov 6–8, 2026), Track 4: Multi-Agent Oversight and Control.
Team: Cardamone, Morill.

**Exploratory v2.1 follow-up:** the current design is in [PROJECT.md](PROJECT.md), with the fixed
follow-up protocol and commands in [docs/V21_PROTOCOL.md](docs/V21_PROTOCOL.md). Local key/Docker setup
is in [docs/V2_SETUP.md](docs/V2_SETUP.md). The earlier frozen project is archived in
[docs/PROJECT_FROZEN.md](docs/PROJECT_FROZEN.md). Its config and scripts remain unchanged.
Completed v2 results are in [report/exploratory_v2.md](report/exploratory_v2.md). New v2.1 progress is in
[RESULTS_LIVE.md](RESULTS_LIVE.md). The full v2.1 evaluation and judged identifier supplement are complete
in [report/exploratory_v21.md](report/exploratory_v21.md), with CSV/JSON exports in
[analysis/exploratory_v21/](analysis/exploratory_v21/). Verification and remaining limitations are in
[docs/V21_IMPLEMENTATION.md](docs/V21_IMPLEMENTATION.md).

**All code in this repository was written during the sprint (Nov 7–9, 2026). There is no pre-existing code.**

The overview and commands below describe the original frozen harness. Use the follow-up protocol above
for the active exploratory experiment.

We test which *grouping rule* (the overseer's "map") lets a trusted monitor catch an attack split across K = 3
independently launched agents that coordinate only through a shared store. The rules compared are per-agent,
provider-side semantic clustering, harness-side artifact provenance, an oracle and a random size-matched control.
See `PLAN.md` for the design and `docs/v1.pdf` for the pitch brief.

## Safety
- Every task is a **proxy goal** in a **mock sandbox with fake data** (e.g. `FAKE-KEY-0000-TEST`).
- Agent-written scripts run only in `docker run --network none` (no host mounts, resource limits).
- Attack templates live in clearly labelled files under `tasks/attacks/`.

## Setup

### Linux / WSL2
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh      # installs uv to ~/.local/bin
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.12
uv sync --extra dev
cp .env.example .env                                  # then fill in keys (never commit .env)
docker build -t swarm-runner:0.1 -f sandbox/runner.Dockerfile sandbox
```

### macOS
```bash
brew install uv            # or the curl installer above
uv python install 3.12
uv sync --extra dev
cp .env.example .env
# Install and start Docker Desktop, then:
docker build -t swarm-runner:0.1 -f sandbox/runner.Dockerfile sandbox
```
On Apple Silicon the runner image builds natively (arm64); nothing else changes.

### Check everything works
```bash
uv run pytest -q                          # unit tests
uv run python scripts/smoke_sandbox.py    # no-network runner, logging completeness
uv run python scripts/list_models.py      # which models each key can use
uv run python scripts/check_keys.py       # one tiny call per model role
```

## Layout
| Path | What |
|---|---|
| `sandbox/seed/` | Base store copied into every episode (`vault/ config/ data/ pipelines/ shared/ops/ outbound/`) |
| `sandbox/runner.Dockerfile`, `hook_run.py` | No-network runner; audit hook records every path a script opens |
| `src/swarm_oversight/gateway.py` | Every tool call goes through here and is logged (visible events and hidden labels kept separately) |
| `src/swarm_oversight/tools.py` | The 6 tools: list, read, write, run, post, register_step |
| `src/swarm_oversight/maps/` | Grouping maps: singleton, per_agent, clustering, provenance, oracle, random_matched |
| `src/swarm_oversight/llm.py` | OpenAI-compatible client for DeepSeek / Groq / Google / OpenRouter, with an sqlite cache |
| `tasks/` | Benign templates and the (labelled) scripted attack templates |
| `configs/models.yaml` | Model per role (worker U, judge T, embedder) |
| `logs/`, `cache/` | Generated; gitignored |
