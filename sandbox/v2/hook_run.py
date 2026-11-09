"""Exploratory v2 wrapper: block child processes; run only inside network-none Docker."""
import contextlib
import io
import json
import os
import runpy
import sys
import traceback


def deny_process(event: str, args: tuple) -> None:
    if event in {"subprocess.Popen", "os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec"}:
        raise PermissionError("exploratory v2 forbids child processes")


def main() -> None:
    os.chdir("/tmp/work")
    script = sys.argv[1]
    sys.argv = sys.argv[1:]
    sys.addaudithook(deny_process)
    output = io.StringIO()
    result = {"ok": True, "stdout": "", "error": "", "paths_read": [], "paths_written": []}
    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            runpy.run_path(script, run_name="__main__")
    except Exception:  # noqa: BLE001 - errors are returned to the host, never treated as successful execution
        result["ok"], result["error"] = False, traceback.format_exc(limit=4)
    result["stdout"] = output.getvalue()[-4000:]
    # The executed driver changes cwd into the store; return metadata outside it.
    with open("/tmp/work/.run_result.json", "w") as handle:
        json.dump(result, handle)


if __name__ == "__main__":
    main()
