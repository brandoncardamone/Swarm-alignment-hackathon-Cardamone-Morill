# Exploratory v2.1 judged identifier supplement

Prospective supplement added after launch and the separate zero-cost linkage check, before any judged
identifier results and before the primary attack-piece scores were examined. The primary five-map
protocol, data, scores, hypotheses and policy selection stay unchanged. All supplemental outcomes
are exploratory. No claim of an independently confirmed superiority test is made.

Rationale: the linkage check found that visible business IDs recover all three pieces in every replay.
A graph-only result does not show whether the trusted judge can use that context. Measure that directly,
using the existing fixed traces, unchanged public brief/judge/0–9 scoring, M=9, and both already fixed
calibration policies. This supplements a missing practical comparator; it does not replace a weak
primary result or choose a best policy.

Score the identifier map on all 1,800 calibration and 1,800 benign-reference requests per family and
all three pieces of all 432 primary insertion cases. Use the same paired task/calibration bootstrap
and 2,000 replicates to report identifier safety CIs under both policies. Existing primary metrics must
reproduce identically when the new map is added in memory. Report raw counts and realized benign
reference flag rates, including size-bin support/backoff. Do not infer statistical superiority from
CI overlap. Judge-free linkage and judged safety remain separate claims.

Queue model calls until primary collection/analysis completes. Reuse the SQLite cache and one response
for identical judge inputs. No new Docker execution, U generation, keys or local setup is required.
Preserve source/input hashes and outputs in a separate supplement directory.
Append results to the local v2.1 Markdown only after the primary report exists.
