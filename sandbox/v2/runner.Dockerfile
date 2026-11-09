# Build separately; the frozen runner tag and its files are never replaced.
FROM swarm-runner:0.1
COPY v2/hook_run.py /opt/hook_run.py
COPY --chmod=755 v2/entry.sh /opt/entry.sh
