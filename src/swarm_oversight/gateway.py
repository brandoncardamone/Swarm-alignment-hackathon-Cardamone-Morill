"""Single entry point for every tool call.

1. Log the request (with declared paths) to logs/events/<episode>.jsonl.
2. Ask the overseer; v1 never blocks online, so the default overseer allows everything
   (all grouping maps are replayed offline).
3. Execute only if allowed, then log the outcome with the observed paths.
Hidden labels go to logs/hidden/<episode>.jsonl, never into the visible record.
"""
from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from pathlib import Path

from . import tools
from .config import LOG_DIR
from .events import Event, HiddenLabels
from .sandbox import Sandbox


def allow_all(event: Event, history: list[Event]) -> str:
    return "allow"


class Gateway:
    def __init__(self, sbx: Sandbox, episode_id: str, *, overseer: Callable = allow_all,
                 log_dir: Path = LOG_DIR):
        self.sbx, self.episode_id, self.overseer = sbx, episode_id, overseer
        self.history: list[Event] = []
        (log_dir / "events").mkdir(parents=True, exist_ok=True)
        (log_dir / "hidden").mkdir(parents=True, exist_ok=True)
        self.ev_path = log_dir / "events" / f"{episode_id}.jsonl"
        self.hid_path = log_dir / "hidden" / f"{episode_id}.jsonl"

    def _log(self, path: Path, rec: dict):
        with path.open("a") as f:
            f.write(json.dumps(rec) + "\n")

    def call(self, root_id: str, tool: str, args: dict, thought: str = "", *,
             is_attack: bool = False, piece_index: int | None = None, **labels) -> str:
        rid = f"{self.episode_id}:{len(self.history)}:{uuid.uuid4().hex[:6]}"
        r, w = tools.declared_paths(tool, args)
        ev = Event(request_id=rid, root_id=root_id, request_text=tools.render(tool, args, thought), tool=tool,
                   args=args, paths_read=r, paths_written=w, seq=len(self.history), timestamp=time.time())
        self._log(self.hid_path, HiddenLabels(request_id=rid, episode_id=self.episode_id, is_attack=is_attack,
                                              piece_index=piece_index, **labels).model_dump())
        ev.verdict = self.overseer(ev, self.history)
        self._log(self.ev_path, {"phase": "request", **ev.model_dump()})
        if ev.verdict != "allow":
            ev.ok, result = False, "DENIED by overseer"
        else:
            try:
                result, r2, w2 = tools.execute(self.sbx, tool, args)
                ev.paths_read, ev.paths_written, ev.ok = r2, w2, not result.startswith("FAILED")
            except Exception as e:  # noqa: BLE001 - tool errors are returned to the agent
                result, ev.ok = f"ERROR: {type(e).__name__}: {e}", False
        ev.result_preview = result[:300]
        self._log(self.ev_path, {"phase": "outcome", **ev.model_dump()})
        self.history.append(ev)
        return result


def load_episode(log_dir: Path, episode_id: str) -> tuple[list[dict], list[dict]]:
    """Final (outcome) records + hidden labels for one episode."""
    evs = [json.loads(line) for line in (log_dir / "events" / f"{episode_id}.jsonl").open()]
    hid = [json.loads(line) for line in (log_dir / "hidden" / f"{episode_id}.jsonl").open()]
    return [e for e in evs if e["phase"] == "outcome"], hid
