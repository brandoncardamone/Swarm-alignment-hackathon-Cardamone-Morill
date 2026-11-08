"""Run a script inside /tmp/work and record every path it reads or writes (sys.addaudithook)."""
import io, json, os, runpy, sys, contextlib, traceback

WORK = "/tmp/work"
reads, writes = set(), set()


def _rel(p):
    try:
        p = os.path.abspath(os.fsdecode(p))
    except Exception:
        return None
    if not p.startswith(WORK + "/"):
        return None
    r = os.path.relpath(p, WORK)
    return None if r.startswith(".run_") else r


def hook(event, args):
    if event == "open":
        path, mode, flags = args
        if isinstance(path, int):
            return
        r = _rel(path)
        if r is None:
            return
        m = mode or ""
        is_write = any(c in m for c in "wax+") or (
            flags is not None and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND))
        (writes if is_write else reads).add(r)
    elif event in ("os.remove", "os.unlink", "os.rmdir", "os.mkdir"):
        r = _rel(args[0]); r and writes.add(r)
    elif event == "os.rename" or event == "os.replace":
        for a in args[:2]:
            r = _rel(a); r and writes.add(r)
    elif event in ("os.listdir", "os.scandir"):
        r = _rel(args[0] if args and args[0] is not None else ".")
        r and reads.add(r)


def main():
    script, argv = sys.argv[1], sys.argv[2:]
    os.chdir(WORK)
    out, ok, err = io.StringIO(), True, ""
    sys.addaudithook(hook)
    sys.argv = [script] + argv
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            runpy.run_path(os.path.join(WORK, script), run_name="__main__")
    except SystemExit as e:
        ok = e.code in (None, 0)
    except Exception:
        ok, err = False, traceback.format_exc(limit=3)
    reads.discard(script)
    res = {"ok": ok, "stdout": out.getvalue()[-4000:], "error": err[-2000:],
           "paths_read": sorted(reads | {script}), "paths_written": sorted(writes)}
    with open(os.path.join(WORK, ".run_result.json"), "w") as f:
        json.dump(res, f)


main()
