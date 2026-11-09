"""EXPLORATORY transport-only resume after provider 429; scientific sources unchanged."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import runpy
from datetime import UTC, datetime
from pathlib import Path

from openai import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError

from swarm_oversight import llm

ROOT = Path(__file__).resolve().parents[1]


def transient(error: BaseException) -> bool:
    if isinstance(error, BaseExceptionGroup):
        return all(transient(child) for child in error.exceptions)
    return isinstance(error, (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError, TimeoutError))


class PacedChat:
    """Bound concurrency and stagger starts; cached responses bypass scheduling."""

    def __init__(self, original, concurrency: int, interval: float):
        self.original = original
        self.slots = asyncio.Semaphore(concurrency)
        self.lock = asyncio.Lock()
        self.interval, self.last = interval, 0.0

    async def __call__(self, model, messages, *, cache_tag='', **params):
        key = hashlib.sha256(json.dumps([model, messages, params, cache_tag], sort_keys=True,
                                        default=str).encode()).hexdigest()
        if llm._get(key) is not None:
            return await self.original(model, messages, cache_tag=cache_tag, **params)
        async with self.slots:
            async with self.lock:
                loop = asyncio.get_running_loop()
                delay = self.last + self.interval - loop.time()
                if delay > 0:
                    await asyncio.sleep(delay)
                self.last = loop.time()
            return await self.original(model, messages, cache_tag=cache_tag, **params)


def write_json(path: Path, value: dict) -> None:
    temp = path.with_suffix('.tmp.json')
    temp.write_text(json.dumps(value, indent=2))
    temp.replace(path)


async def resume(args: argparse.Namespace) -> None:
    suffix = 'identifier' if args.supplement else 'primary'
    source = ROOT / 'scripts' / ('exploratory_v21_identifier_eval.py' if args.supplement else 'exploratory_v21.py')
    namespace = runpy.run_path(str(source))
    path = args.run / f'exploratory_transport_{suffix}_amendment.json'
    digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if path.exists():
        if json.loads(path.read_text())['wrapper_sha256'] != digest:
            raise ValueError('transport wrapper changed; preserve/version the amendment')
    else:
        write_json(path, {'analysis': 'exploratory_v21', 'recorded_utc': datetime.now(UTC).isoformat(),
            'wrapper_sha256': digest, 'stage': suffix, 'reason': 'Provider HTTP 429 exhausted existing retries at 11 calibration batches; no attack-piece outcomes yet.',
            'initial_concurrency': args.concurrency, 'initial_start_interval_seconds': args.interval,
            'bounded_attempts': 3, 'retry_pause_seconds': 30,
            'unchanged': 'Prompts, data, maps, models/params, seeds, q, calibration policies, completed scores and scientific source hashes.'})
    if args.supplement:
        namespace['record_plan'](args.run)
        while not (args.run / 'exploratory_summary.json').exists():
            await asyncio.sleep(5)
    status_file = args.run / f'exploratory_transport_{suffix}_status.json'
    original = llm.chat
    for attempt in range(3):
        concurrency = max(2, args.concurrency // 2**attempt)
        interval = min(1.4, args.interval * 2**attempt)
        state = {'phase': 'Running', 'stage': suffix, 'attempt': attempt+1,
                 'concurrency': concurrency, 'start_interval_seconds': interval, 'pid': os.getpid(),
                 'updated_utc': datetime.now(UTC).isoformat()}
        write_json(status_file, state)
        llm.chat = PacedChat(original, concurrency, interval)
        try:
            if args.supplement:
                await namespace['evaluate'](args.run, args)
            else:
                await namespace['collect'](args.run, args)
        except BaseException as error:
            retry = transient(error) and attempt < 2
            write_json(status_file, {**state, 'phase': 'Retrying after provider/network error' if retry else 'Stopped',
                       'updated_utc': datetime.now(UTC).isoformat(), 'error_type': type(error).__name__,
                       'transient': transient(error)})
            if not retry:
                raise
            print(f'Transient provider failure; checkpoint/cache preserved. Retrying with less concurrency in 30 seconds (attempt {attempt+2}/3).', flush=True)
            await asyncio.sleep(30)
        else:
            write_json(status_file, {**state, 'phase': 'Succeeded', 'updated_utc': datetime.now(UTC).isoformat()})
            break
        finally:
            llm.chat = original
    if args.supplement:
        while not (args.run / 'exploratory_report_complete.json').exists():
            await asyncio.sleep(5)
        namespace['append_report'](args.run)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--supplement', action='store_true')
    parser.add_argument('--allow-api', action='store_true')
    parser.add_argument('--estimated-cost-usd', required=True, type=float)
    parser.add_argument('--remaining-budget-usd', type=float, default=23)
    parser.add_argument('--concurrency', type=int, default=8)
    parser.add_argument('--interval', type=float, default=.35)
    args = parser.parse_args()
    if not args.allow_api or args.estimated_cost_usd <= 0 or args.concurrency < 1 or args.interval < 0:
        raise ValueError('explicit API opt-in, positive estimate and valid pacing required')
    asyncio.run(resume(args))


if __name__ == '__main__':
    main()
