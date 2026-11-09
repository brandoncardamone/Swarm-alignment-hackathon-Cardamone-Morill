#!/bin/sh
# EXPLORATORY: return wrapper startup errors instead of silently archiving a failed run.
set -eu
mkdir -p /tmp/work
cd /tmp/work
tar -x
timeout 180 python /opt/hook_run.py "$@" > /dev/null
tar -c -C /tmp/work .
