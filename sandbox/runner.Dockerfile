# Executes agent-written scripts. Always run with: docker run --rm -i --network none
# Everything is installed at build time; nothing is installed while agents run.
FROM python:3.12-slim
RUN pip install --no-cache-dir pyyaml==6.0.2 && useradd -m runner
COPY hook_run.py /opt/hook_run.py
COPY entry.sh /opt/entry.sh
RUN chmod +x /opt/entry.sh
USER runner
ENTRYPOINT ["/opt/entry.sh"]
