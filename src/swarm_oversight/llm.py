"""Provider-agnostic chat/embedding client (OpenAI-compatible endpoints) with a sqlite cache.

Model strings look like 'provider/model-id', e.g. 'groq/llama-3.1-8b-instant'.
Every call is cached by a hash of (model, messages, params), so reruns are free.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
import threading
import time

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, InternalServerError, RateLimitError

RETRYABLE = (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError)

from .config import CACHE_DIR, PROVIDERS, api_key

_clients: dict[str, AsyncOpenAI] = {}
_lock = threading.Lock()
_sems: dict[str, asyncio.Semaphore] = {}
CONCURRENCY = {"deepseek": 32, "groq": 8, "google": 8, "openrouter": 8}

USAGE = {"calls": 0, "cached": 0, "prompt_tokens": 0, "completion_tokens": 0}


def _db():
    CACHE_DIR.mkdir(exist_ok=True)
    con = sqlite3.connect(CACHE_DIR / "llm_cache.sqlite", check_same_thread=False)
    con.execute("CREATE TABLE IF NOT EXISTS c (k TEXT PRIMARY KEY, v TEXT)")
    return con


_con = _db()


def _get(k):
    with _lock:
        r = _con.execute("SELECT v FROM c WHERE k=?", (k,)).fetchone()
    return json.loads(r[0]) if r else None


def _put(k, v):
    with _lock:
        _con.execute("INSERT OR REPLACE INTO c VALUES (?,?)", (k, json.dumps(v)))
        _con.commit()


def split(model: str) -> tuple[str, str]:
    provider, _, mid = model.partition("/")
    return provider, mid


def client(provider: str) -> AsyncOpenAI:
    if provider not in _clients:
        base, _ = PROVIDERS[provider]
        _clients[provider] = AsyncOpenAI(base_url=base, api_key=api_key(provider), max_retries=5, timeout=120)
    return _clients[provider]


def _sem(provider):
    if provider not in _sems:
        _sems[provider] = asyncio.Semaphore(CONCURRENCY.get(provider, 8))
    return _sems[provider]


async def chat(model: str, messages: list[dict], *, cache_tag: str = "", **params) -> dict:
    """Returns the first choice as a plain dict (message, logprobs, usage). Cached."""
    key = hashlib.sha256(json.dumps([model, messages, params, cache_tag], sort_keys=True,
                                    default=str).encode()).hexdigest()
    hit = _get(key)
    if hit is not None:
        USAGE["cached"] += 1
        return hit
    provider, mid = split(model)
    async with _sem(provider):
        for attempt in range(6):
            try:
                r = await client(provider).chat.completions.create(model=mid, messages=messages, **params)
                break
            except RETRYABLE:
                if attempt == 5:
                    raise
                await asyncio.sleep(min(60, 2 ** attempt + 0.5))
    ch = r.choices[0]
    out = {"message": ch.message.model_dump(exclude_none=True),
           "logprobs": ch.logprobs.model_dump() if getattr(ch, "logprobs", None) else None,
           "finish_reason": ch.finish_reason,
           "usage": r.usage.model_dump() if r.usage else None}
    USAGE["calls"] += 1
    if r.usage:
        USAGE["prompt_tokens"] += r.usage.prompt_tokens or 0
        USAGE["completion_tokens"] += r.usage.completion_tokens or 0
    _put(key, out)
    return out


async def embed(model: str, texts: list[str]) -> list[list[float]]:
    """Embeddings through the OpenAI-compatible endpoint, cached per text."""
    provider, mid = split(model)
    keys = [hashlib.sha256(json.dumps([model, t]).encode()).hexdigest() for t in texts]
    out: list = [_get(k) for k in keys]
    todo = [i for i, v in enumerate(out) if v is None]
    for s in range(0, len(todo), 64):
        idx = todo[s:s + 64]
        async with _sem(provider):
            r = await client(provider).embeddings.create(model=mid, input=[texts[i] for i in idx])
        for i, d in zip(idx, r.data):
            out[i] = d.embedding
            _put(keys[i], d.embedding)
    return out


def timed(coro_fn):
    async def w(*a, **k):
        t = time.perf_counter()
        r = await coro_fn(*a, **k)
        return r, time.perf_counter() - t
    return w
