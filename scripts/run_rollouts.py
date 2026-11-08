"""Main rollouts: benign pool + evaluation attack episodes (1 rollout per task x attack; v1 §4)."""
import asyncio
import sys

from swarm_oversight import llm
from swarm_oversight.episodes import run_attack, run_benign
from tasks.attacks.ATTACK_TEMPLATES_proxy_goals import ATTACKS, FAMILIES, N_DEV, N_EVAL

N_BENIGN = int(sys.argv[1]) if len(sys.argv) > 1 else 600
BATCH = 40


async def batched(coros):
    out = []
    for s in range(0, len(coros), BATCH):
        out += await asyncio.gather(*coros[s:s + BATCH], return_exceptions=True)
        print(f"  {len(out)}/{len(coros)} done; usage={llm.USAGE}", flush=True)
    return out


async def main():
    atk = [run_attack(f, a, k) for k in range(N_DEV, N_DEV + N_EVAL) for f in FAMILIES for a in ATTACKS]
    res = await batched(atk)
    ok = [r for r in res if isinstance(r, dict)]
    print(f"attacks: {len(ok)} ran, {sum(r['completed'] for r in ok)} completed, {len(res) - len(ok)} errors", flush=True)
    for r in res:
        if not isinstance(r, dict):
            print("  ERROR", repr(r)[:200])
    ben = await batched([run_benign(i, seed=0, split="pool") for i in range(N_BENIGN)])
    print(f"benign: {sum(isinstance(r, dict) for r in ben)} ran, {sum(not isinstance(r, dict) for r in ben)} errors")

asyncio.run(main())
