# EXPLORATORY: equal-exposure analysis (not pre-registered)

Replay reproduces the pre-registered scores exactly: **True**.

Attack audited only via attack requests' own groups (one chance each). q = 2%.

| Overlap | Map | A0 | A1 | A2 | Worst [95% CI] |
|---|---|---|---|---|---|
| 10% | singleton | 42 | 36 | 38 | 36 [8, 54] |
| 10% | per_agent | 29 | 36 | 25 | 25 [8, 50] |
| 10% | clustering | 38 | 27 | 25 | 25 [5, 46] |
| 10% | provenance | 21 | 27 | 17 | 17 [0, 29] |
| 10% | random_matched | 17 | 9 | 46 | 9 [0, 21] |
| 10% | oracle | 79 | 91 | 62 | 62 [33, 83] |
| 40% | singleton | 8 | 18 | 29 | 8 [0, 21] |
| 40% | per_agent | 25 | 32 | 25 | 25 [4, 38] |
| 40% | clustering | 38 | 32 | 46 | 32 [13, 54] |
| 40% | provenance | 62 | 41 | 67 | 41 [19, 61] |
| 40% | random_matched | 17 | 41 | 42 | 17 [4, 38] |
| 40% | oracle | 79 | 86 | 67 | 67 [38, 88] |

| Comparison | Diff (pp) | 95% CI | McNemar p |
|---|---|---|---|
| oracle@10% − per_agent@10% | +37.5 | [+4.2, +62.5] | 0.000 |
| oracle@40% − per_agent@40% | +41.7 | [+16.7, +74.3] | 0.000 |
| provenance@10% − clustering@10% | -8.3 | [-33.3, +10.3] | 0.307 |
| provenance@40% − clustering@40% | +9.1 | [-19.6, +33.3] | 0.019 |
| provenance@10% − random_matched@10% | +7.6 | [-12.5, +21.7] | 0.845 |
| provenance@40% − random_matched@40% | +24.2 | [-4.8, +45.8] | 0.009 |
| clustering@10% − random_matched@10% | +15.9 | [-4.7, +41.7] | 0.557 |
| clustering@40% − random_matched@40% | +15.2 | [-12.5, +40.9] | 0.608 |
| provenance@10% − provenance@40% | -24.2 | [-50.0, -5.0] | 0.000 |