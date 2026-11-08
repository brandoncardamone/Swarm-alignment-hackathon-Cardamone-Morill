"""Sandbox smoke test: no network in the runner, mock endpoint round-trip, read/write/run paths logged."""
import json
import subprocess
import tempfile
from pathlib import Path

from swarm_oversight.config import RUNNER_IMAGE
from swarm_oversight.gateway import Gateway, load_episode
from swarm_oversight.sandbox import Sandbox

ok = True
def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    print(f"{'PASS' if cond else 'FAIL'}  {name} {detail}")

# 1. No network inside the runner container
p = subprocess.run(["docker", "run", "--rm", "--network", "none", "--entrypoint", "python", RUNNER_IMAGE, "-c",
                    "import socket\ntry:\n socket.gethostbyname('example.com'); print('RESOLVED')\nexcept Exception as e: print('NO-DNS', type(e).__name__)"],
                   capture_output=True, text=True, check=False)
check("DNS lookup fails in runner", "NO-DNS" in p.stdout, p.stdout.strip())

log = Path(tempfile.mkdtemp())
sbx = Sandbox()
try:
    gw = Gateway(sbx, "smoke", log_dir=log)
    gw.call("r1", "read", {"path": "data/toy_labels.csv"})
    gw.call("r1", "write", {"path": "pipelines/steps/count.py", "content":
        "import csv\nrows=list(csv.DictReader(open('data/toy_labels.csv')))\n"
        "open('shared/ops/count.txt','w').write(str(len(rows)))\nprint(len(rows))\n"})
    out = gw.call("r2", "run", {"script_path": "pipelines/steps/count.py"})
    gw.call("r3", "post", {"endpoint": "status", "body": "count done", "attach_path": "shared/ops/count.txt"})
    gw.call("r3", "register_step", {"pipeline": "train_sentiment", "name": "count", "script_path": "pipelines/steps/count.py"})
    evs, hid = load_episode(log, "smoke")
    run_ev = evs[2]
    check("run executes script", out.startswith("ok") and "60" in out, repr(out[:40]))
    check("run logs observed reads", "data/toy_labels.csv" in run_ev["paths_read"], run_ev["paths_read"])
    check("run logs observed writes", run_ev["paths_written"] == ["shared/ops/count.txt"], run_ev["paths_written"])
    posted = [json.loads(line) for line in sbx.p("outbound/status.jsonl").open()]
    check("mock endpoint round-trip", posted and "60" in posted[0]["body"], posted[0]["body"][-20:] if posted else "")
    check("post logs attach read + outbound write", evs[3]["paths_read"] == ["shared/ops/count.txt"] and
          evs[3]["paths_written"] == ["outbound/status.jsonl"])
    check("register_step updates registry", "count.py" in sbx.read("pipelines/registry.yaml"))
    check("every call logged twice (request+outcome)", sum(1 for _ in (log / "events" / "smoke.jsonl").open()) == 10)
    # completeness: files changed on disk vs files the log says were written
    seed = Sandbox()
    changed = {str(f.relative_to(sbx.dir)) for f in sbx.dir.rglob("*") if f.is_file() and
               (not seed.p(str(f.relative_to(sbx.dir))).exists() or seed.p(str(f.relative_to(sbx.dir))).read_bytes() != f.read_bytes())}
    logged = {w for e in evs for w in e["paths_written"]}
    seed.cleanup()
    check("log covers every changed file", changed <= logged, f"changed={sorted(changed)}")
finally:
    sbx.cleanup()
print("SMOKE", "OK" if ok else "FAILED")
