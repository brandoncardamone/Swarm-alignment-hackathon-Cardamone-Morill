Filter files: YAML with a `filters:` list. Each filter: {name, logger, drop_level}.
`logger` is a logger name or '*'. A record is dropped if its level has the same numeric value as `drop_level`.
A filter file is active only once it is listed under `includes:` in config/logging.yaml.
