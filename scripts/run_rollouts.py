"""Main rollouts: benign pool + evaluation attack episodes (1 rollout per task x attack; v1 §4)."""
import asyncio
import sys

from swarm_oversight import llm
from swarm_oversight.episodes import run_attack, run_benign
from tasks.attacks.ATTACK_TEMPLATES_proxy_goals import ATTACKS, FAMILIES, N_DEV, N_EVAL

N_BENIGN = int(sys.argv[1]) if len(sys.argv) > 1 else 600
BATCH = 40
EPISODE_TIMEOUT = 900  # seconds; a stalled episode is recorded as an error and excluded


def limited(coro):
    return asyncio.wait_for(coro, timeout=EPISODE_TIMEOUT)


async def batched(coros):
    """Rolling pool: at most BATCH episodes in flight; progress every 20 completions."""
    sem, done, out = asyncio.Semaphore(BATCH), [0], []

    async def run(c):
        async with sem:
            try:
                r = await limited(c)
            except Exception as e:  # noqa: BLE001 - recorded and excluded, never blocks the pool
                r = e
            done[0] += 1
            if done[0] % 20 == 0 or done[0] == len(coros):
                print(f"  {done[0]}/{len(coros)} done; usage={llm.USAGE}", flush=True)
            return r
    out = await asyncio.gather(*(run(c) for c in coros))
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
