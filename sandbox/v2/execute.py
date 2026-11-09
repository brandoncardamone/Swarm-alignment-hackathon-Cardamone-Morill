"""EXPLORATORY trusted batch executor, invoked ONLY inside the v2 Docker image.

The whole stream is a speculative offline execution, with no externally visible
effects until the archive is returned. Runtime paths support hypothetical audit
decisions; this is not an online implementation of pre-execution tracing.
"""
import hashlib
import json
import os
import runpy
import sys
from pathlib import Path

ROOT = Path("/tmp/work/store")
READS: set[str] = set()
WRITES: set[str] = set()
ACTIVE = False


def hook(event: str, args: tuple) -> None:
    if not ACTIVE or event != "open" or isinstance(args[0], int):
        return
    path = Path(os.path.abspath(os.fsdecode(args[0])))
    if not path.is_relative_to(ROOT):
        return
    name = str(path.relative_to(ROOT))
    mode, flags = args[1], args[2]
    writing = any(c in (mode or "") for c in "wax+") or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)
    (WRITES if writing else READS).add(name)


def path(value: str) -> Path:
    result = (ROOT / value).resolve()
    if not result.is_relative_to(ROOT):
        raise ValueError("store escape")
    return result


def snapshot() -> dict[str, str]:
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in ROOT.rglob("*") if p.is_file()}


def execute(step: dict) -> None:
    args, tool = step["args"], step["tool"]
    if tool == "read":
        path(args["path"]).read_text()
    elif tool in ("append", "write"):
        target = path(args["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a" if tool == "append" else "w") as handle:
            handle.write(json.dumps(args["record"]) + "\n" if tool == "append" else args["content"])
    elif tool == "run":
        runpy.run_path(str(path(args["script_path"])), run_name="__main__",
                       init_globals={"SKIP": args.get("skip_token_check", False)})
    elif tool == "register_step":
        path(args["artifact"]).read_text()
        target = path(args["registry"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"artifact": args["artifact"], "enabled": True}))
    else:
        raise ValueError(f"unsupported tool {tool}")


def main() -> None:
    global ACTIVE
    plan = json.loads(Path("/tmp/work/plan.json").read_text())
    os.chdir(ROOT)
    sys.dont_write_bytecode = True
    sys.addaudithook(hook)
    events, hidden, failures = [], {}, []
    before = snapshot()
    all_writes: set[str] = set()
    with Path("/tmp/work/requests.jsonl").open("w") as requests:
        for i, item in enumerate(plan):
            step, label = item
            rid = f"request-{i}"
            event = {"request_id": rid, "root_id": step["root_id"], "tool": step["tool"],
                     "args": step["args"], "request_text": step["request_text"], "stream_position": i}
            requests.write(json.dumps(event) + "\n")
            requests.flush()  # record before executing
            READS.clear()
            WRITES.clear()
            ACTIVE = True
            try:
                execute(step)
                event["ok"] = True
            except Exception as error:  # noqa: BLE001 - record tool failure and fail the enclosing replay
                event["ok"] = False
                failures.append({"position": i, "error": type(error).__name__})
            finally:
                ACTIVE = False
            all_writes.update(WRITES)
            event.update(paths_read=sorted(READS), paths_written=sorted(WRITES))
            events.append(event)
            hidden[rid] = label
    after = snapshot()
    changed = {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)}
    if not changed <= all_writes:
        raise RuntimeError(f"unlogged writes: {sorted(changed - all_writes)}")
    Path("/tmp/work/events.json").write_text(json.dumps(events))
    Path("/tmp/work/hidden.json").write_text(json.dumps(hidden))
    Path("/tmp/work/failures.json").write_text(json.dumps(failures))


if __name__ == "__main__":
    main()
