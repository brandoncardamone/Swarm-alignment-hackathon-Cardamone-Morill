"""A sandbox is a private copy of the seed store. Tools operate on relative paths inside it.

Only `run` executes model-written code, and only inside `docker run --rm -i --network none`
with the store piped in and out as a tar archive (no host mounts).
"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
import tarfile
import tempfile
import uuid
from pathlib import Path, PurePosixPath

from .config import RUNNER_IMAGE, SEED_DIR


class PathError(ValueError):
    pass


def norm(path: str) -> str:
    p = PurePosixPath(str(path).strip().lstrip("/"))
    if any(part == ".." for part in p.parts) or str(p) in ("", "."):
        raise PathError(f"invalid path: {path!r}")
    return str(p)


class Sandbox:
    def __init__(self, base: Path | None = None):
        self.dir = Path(tempfile.mkdtemp(prefix="swarm_sbx_"))
        shutil.copytree(base or SEED_DIR, self.dir, dirs_exist_ok=True)

    def p(self, rel: str) -> Path:
        return self.dir / norm(rel)

    def cleanup(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    # --- primitives used by tools.py ---
    def list(self, rel: str) -> list[str]:
        d = self.dir if rel in ("", ".", "/") else self.p(rel)
        if not d.is_dir():
            raise FileNotFoundError(rel)
        return sorted(str(x.relative_to(self.dir)) + ("/" if x.is_dir() else "") for x in d.iterdir()
                      if not x.name.startswith(".run_"))

    def read(self, rel: str) -> str:
        return self.p(rel).read_text()[:20000]

    def write(self, rel: str, content: str):
        f = self.p(rel)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)

    def append(self, rel: str, line: str):
        f = self.p(rel)
        f.parent.mkdir(parents=True, exist_ok=True)
        with f.open("a") as fh:
            fh.write(line + "\n")

    def run(self, script: str, args: list[str] | None = None, timeout: int = 60) -> dict:
        script = norm(script)
        if not self.p(script).is_file():
            raise FileNotFoundError(script)
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as t:
            t.add(self.dir, arcname=".")
        name = f"swarm_run_{uuid.uuid4().hex[:10]}"
        proc = subprocess.run(
            ["docker", "run", "--rm", "-i", "--name", name, "--network", "none", "--memory", "256m",
             "--cpus", "1", "--pids-limit", "64", "--read-only", "--tmpfs", "/tmp:rw,size=64m",
             RUNNER_IMAGE, script, *[str(a) for a in (args or [])]],
            input=buf.getvalue(), capture_output=True, timeout=timeout, check=False)
        if proc.returncode != 0:
            return {"ok": False, "stdout": "", "error": proc.stderr.decode()[-1000:],
                    "paths_read": [script], "paths_written": []}
        # Replace the store with the container's output (safe extraction only).
        new = Path(tempfile.mkdtemp(prefix="swarm_sbx_"))
        with tarfile.open(fileobj=io.BytesIO(proc.stdout)) as t:
            t.extractall(new, filter="data")
        res_file = new / ".run_result.json"
        res = json.loads(res_file.read_text()) if res_file.exists() else {
            "ok": False, "stdout": "", "error": "no result", "paths_read": [script], "paths_written": []}
        res_file.unlink(missing_ok=True)
        shutil.rmtree(self.dir)
        new.rename(self.dir)
        return res
