"""One tiny call per candidate model: OK/FAIL, latency, and whether logprobs come back. Never prints keys."""
import asyncio
import sys
import time

from swarm_oversight import llm

CANDIDATES = {
    "worker": [("openrouter/deepseek/deepseek-v4-flash", {"extra_body": {"reasoning": {"enabled": False}}}),
               ("deepseek/deepseek-flash", {"reasoning_effort": "none"})],
    "judge": [("openrouter/meta-llama/llama-3.1-8b-instruct", {"extra_body": {"provider": {"require_parameters": True}}}),
              ("openrouter/mistralai/mistral-small-3.2-24b-instruct", {"extra_body": {"provider": {"require_parameters": True}}}),
              ("groq/llama-3.1-8b-instant", {})],
    "embedder": [("google/gemini-embedding-001", None)],
}
MSG = [{"role": "user", "content": "Reply with exactly: OK"}]


async def one(role, model, extra):
    t = time.perf_counter()
    try:
        if extra is None:
            v = (await llm.embed(model, [f"probe {time.time()}"]))[0]
            return f"{role:9} {model:48} OK   {time.perf_counter()-t:5.2f}s  dim={len(v)}"
        params = dict(extra, max_tokens=5, temperature=0)
        if role == "judge":
            params.update(logprobs=True, top_logprobs=5)
        r = await llm.chat(model, MSG, cache_tag=str(time.time()), **params)
        txt = (r["message"].get("content") or "").strip()[:12]
        lp = bool(r["logprobs"] and r["logprobs"].get("content"))
        return f"{role:9} {model:48} {'OK  ' if 'OK' in txt else 'ODD '} {time.perf_counter()-t:5.2f}s  reply={txt!r} logprobs={lp}"
    except Exception as e:  # noqa: BLE001
        return f"{role:9} {model:48} FAIL {type(e).__name__}: {str(e)[:110]}"


async def main():
    jobs = [one(r, m, x) for r, lst in CANDIDATES.items() for m, x in lst]
    for line in await asyncio.gather(*jobs):
        print(line)
    sys.stdout.flush()

asyncio.run(main())
