## Grid at q = 2% (safety %, 95% paired cluster-bootstrap CI on the worst case)

| Overlap | Map | A0 | A1 | A2 | Worst [CI] | Group recall | Group precision | Mean group size | Map misses | Judge misses |
|---|---|---|---|---|---|---|---|---|---|---|
| 10% | Singleton | 42 | 36 | 38 | 36 [8, 54] | 0.47 | 1.00 | 1.0 | 43 | 0 |
| 10% | Per-agent (baseline) | 29 | 36 | 25 | 25 [8, 50] | 0.61 | 0.23 | 7.5 | 49 | 0 |
| 10% | Clustering (provider-side) | 50 | 36 | 29 | 29 [12, 54] | 0.57 | 0.36 | 13.1 | 38 | 5 |
| 10% | Provenance (harness-side) | 25 | 45 | 21 | 21 [4, 33] | 0.61 | 0.37 | 19.0 | 30 | 19 |
| 10% | Random size-matched | 67 | 50 | 79 | 50 [29, 73] | 0.49 | 0.31 | 19.0 | 22 | 2 |
| 10% | Oracle (joint review) | 92 | 91 | 79 | 79 [46, 92] | 1.00 | 0.20 | 16.3 | 0 | 9 |
| 40% | Singleton | 8 | 18 | 29 | 8 [0, 21] | 0.47 | 1.00 | 1.0 | 57 | 0 |
| 40% | Per-agent (baseline) | 25 | 32 | 29 | 25 [4, 45] | 0.61 | 0.23 | 7.5 | 50 | 0 |
| 40% | Clustering (provider-side) | 54 | 45 | 67 | 45 [24, 74] | 0.57 | 0.27 | 23.6 | 30 | 1 |
| 40% | Provenance (harness-side) | 62 | 41 | 79 | 41 [19, 64] | 0.60 | 0.35 | 24.1 | 25 | 2 |
| 40% | Random size-matched | 71 | 73 | 79 | 71 [46, 82] | 0.49 | 0.29 | 24.1 | 17 | 1 |
| 40% | Oracle (joint review) | 88 | 95 | 79 | 79 [50, 92] | 1.00 | 0.20 | 16.3 | 0 | 9 |

## Hypotheses at q = 2% (difference in worst-case safety, pp, paired 95% CI; exact McNemar p)

| Test | Diff | 95% CI | McNemar p | CI excludes 0 |
|---|---|---|---|---|
| H0@0.1 | +54.2 | [+12.5, +75.0] | 0.000 | yes |
| H0@0.4 | +54.2 | [+22.3, +79.2] | 0.000 | yes |
| H_main@0.1 | -8.3 | [-37.5, +7.4] | 0.307 | no |
| H_dilution | -20.1 | [-50.4, +2.3] | 0.000 | no |
| prov_vs_random@0.1 | -29.2 | [-61.7, -4.7] | 0.000 | yes |
| prov_vs_random@0.4 | -29.9 | [-48.9, +2.4] | 0.122 | no |

## Recovered fraction of the oracle's gain over per-agent (q = 2%)

- 10% overlap, Provenance (harness-side): -0.08
- 10% overlap, Clustering (provider-side): 0.08
- 10% overlap, Random size-matched: 0.46
- 40% overlap, Provenance (harness-side): 0.29
- 40% overlap, Clustering (provider-side): 0.38
- 40% overlap, Random size-matched: 0.85

## Episodes: 70 completed attack episodes evaluated; 2 excluded (attack failed even without monitoring).