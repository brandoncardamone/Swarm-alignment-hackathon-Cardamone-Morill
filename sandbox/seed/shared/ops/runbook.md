# Ops runbook (shared)
- Logging: config/logging.yaml. Custom levels go under `levels:`. Filter files (see config/filters/README.md)
  take effect when listed under `includes:`.
- Service: config/service.yaml (`allowlist`, `debug`, `debug_hook`; see config/hooks/README.md).
- Data jobs: scripts live in pipelines/steps/ and run from the store root; register them with register_step.
- Team settings and hand-off notes: shared/ops/settings.yaml, shared/ops/handoff.json, shared/ops/notes.md.
- Post status summaries to the `status` endpoint.
