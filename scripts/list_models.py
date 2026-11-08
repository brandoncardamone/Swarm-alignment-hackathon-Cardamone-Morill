"""List models available to each key (names only; keys are never printed)."""
import asyncio
import re
import sys

from swarm_oversight.config import PROVIDERS, api_key
from swarm_oversight.llm import client

PATTERNS = {"deepseek": r".", "groq": r".", "google": r"flash|embed|gemma",
            "openrouter": r"(deepseek|llama-3\.[12]-8b|gemini.*(flash|lite)|qwen.*(7b|8b|14b)|mistral.*small)"}


async def main():
    for p in PROVIDERS:
        if not api_key(p):
            print(f"## {p}: key missing"); continue
        try:
            ids = sorted(m.id for m in (await client(p).models.list()).data)
        except Exception as e:  # noqa: BLE001
            print(f"## {p}: ERROR {type(e).__name__}: {str(e)[:150]}"); continue
        keep = [i for i in ids if re.search(PATTERNS[p], i, re.IGNORECASE)]
        print(f"## {p}: {len(ids)} models, showing {len(keep)}")
        for i in keep[:60]:
            print("  ", i)
    sys.stdout.flush()

asyncio.run(main())
