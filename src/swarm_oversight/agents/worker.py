"""Worker loop (untrusted model U). Each root is launched with fresh, separate state.
TODO(next step): system prompt = cover task (+ scripted piece for attack roots, delivered via prompt,
which is the one unlogged channel); loop: chat -> tool_calls -> Gateway.call -> tool results; stop when no tool call."""
