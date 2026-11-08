"""Dry run: one dev attack episode + a couple of benign episodes. Prints what each root did."""
import asyncio
import sys

from swarm_oversight import llm
from swarm_oversight.config import LOG_DIR
from swarm_oversight.episodes import run_attack, run_benign
from swarm_oversight.gateway import load_episode

fam = sys.argv[1] if len(sys.argv) > 1 else "audit_off"
atk = sys.argv[2] if len(sys.argv) > 2 else "A0"


async def main():
    metas = await asyncio.gather(run_attack(fam, atk, 0), run_benign(0), run_benign(1))
    for m in metas:
        evs, hid = load_episode(LOG_DIR, m["episode_id"])
        lab = {h["request_id"]: h for h in hid}
        print(f"\n=== {m['episode_id']} kind={m['kind']} "
              f"{'completed=' + str(m['completed']) if m['kind'] == 'attack' else 'template=' + m['template']}")
        for e in evs:
            tag = "ATK" if lab[e["request_id"]]["is_attack"] else "   "
            print(f" {tag} {e['root_id']} {e['tool']:13} ok={e['ok']!s:5} R={e['paths_read']} W={e['paths_written']}")
    print("\nusage:", llm.USAGE)

asyncio.run(main())
