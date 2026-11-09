"""EXPLORATORY security regression probe. Execute inside Docker only."""
import json
import os
import socket
import subprocess
from pathlib import Path


def main() -> None:
    result = {"dns_blocked": False, "subprocess_blocked": False}
    socket.setdefaulttimeout(2)
    try:
        socket.gethostbyname("example.com")
    except OSError:
        result["dns_blocked"] = True
    try:
        subprocess.run(["/bin/sh", "-c", "true"], check=True)
    except PermissionError:
        result["subprocess_blocked"] = True
    Path("/tmp/work/security.json").write_text(json.dumps(result))
    os.chdir("/tmp")  # regression: wrapper must still write /tmp/work/.run_result.json


if __name__ == "__main__":
    main()
