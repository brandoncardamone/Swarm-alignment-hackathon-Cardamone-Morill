#!/bin/sh
# stdin: tar of the sandbox store. stdout: tar of the store after the run (incl. .run_result.json).
set -e
mkdir -p /tmp/work && cd /tmp/work && tar -x
timeout 30 python /opt/hook_run.py "$@" > /dev/null 2>&1 || true
tar -c -C /tmp/work .
