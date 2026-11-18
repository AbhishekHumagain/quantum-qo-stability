# JOB pilot manifest

Performance-blind selection; one variant per template. No JOB runtimes measured.

| Query | Template | Relations | Edges | Cycle rank | Self join | Stratum |
|---|---:|---:|---:|---:|---|---|
| 3a | 3 | 4 | 4 | 1 | False | small |
| 16a | 16 | 8 | 11 | 4 | False | small |
| 10a | 10 | 7 | 7 | 1 | False | small |
| 18a | 18 | 7 | 9 | 3 | True | small |
| 21a | 21 | 9 | 14 | 6 | False | medium |
| 23a | 23 | 11 | 16 | 6 | False | medium |
| 25a | 25 | 9 | 14 | 6 | True | medium |
| 13a | 13 | 9 | 11 | 3 | True | medium |
| 26a | 26 | 12 | 17 | 6 | True | large |
| 29a | 29 | 17 | 28 | 12 | True | large |
| 24a | 24 | 12 | 18 | 7 | False | large |
| 28a | 28 | 14 | 23 | 10 | True | large |

Catalog: 113 instances, 33 templates.
All-instance size strata: {'small': 62, 'medium': 31, 'large': 20}.

Graph edges reflect explicit cross-alias equality predicates, including redundant equalities;
cycle rank is not a count of independent semantic join constraints.
