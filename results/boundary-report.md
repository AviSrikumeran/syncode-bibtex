# Measured test spectrum

| Category | Expectations met | Median case time (ms) |
| --- | --- | --- |
| regression-valid | 41/41 | 0.0424 |
| regression-invalid | 24/24 | 0.0597 |
| nesting-valid | 8/8 | 0.1380 |
| nesting-invalid | 8/8 | 0.2298 |
| document-size-valid | 4/4 | 2.3053 |
| document-size-invalid | 4/4 | 2.4164 |
| value-length-valid | 5/5 | 0.0403 |
| value-length-invalid | 5/5 | 0.0862 |
| feature-interactions | 48/48 | 0.0955 |
| every-prefix-truncation | 58/58 | 0.1021 |
| semantic-limits-accepted | 5/5 | 0.0625 |
| documented-out-of-scope | 4/4 | 0.0335 |
| lexical-boundary | 2/2 | 0.0304 |
| unicode-content | 1/1 | 0.0511 |

## Scaling observations

| Case | Characters | Accepted | Median ms |
| --- | --- | --- | --- |
| depth-0 | 18 | True | 0.0401 |
| depth-1 | 20 | True | 0.0429 |
| depth-2 | 22 | True | 0.0474 |
| depth-8 | 34 | True | 0.0736 |
| depth-40 | 98 | True | 0.2024 |
| depth-100 | 218 | True | 0.4484 |
| depth-500 | 1018 | True | 2.1216 |
| depth-1000 | 2018 | True | 4.0370 |
| entries-1 | 27 | True | 0.0491 |
| entries-10 | 279 | True | 0.4109 |
| entries-100 | 2979 | True | 4.1997 |
| entries-1000 | 31779 | True | 48.3594 |
| characters-0 | 17 | True | 0.0403 |
| characters-1 | 18 | True | 0.0389 |
| characters-100 | 117 | True | 0.0382 |
| characters-10000 | 10017 | True | 0.0502 |
| characters-100000 | 100017 | True | 0.1385 |

Unexpected outcomes: 0.


Timings describe this machine and run, not a controlled performance benchmark.
The largest case tested is not a proven maximum. This is selected boundary coverage, not exhaustive BibTeX conformance.
Out-of-scope rejection does not mean those BibTeX features are invalid. Semantic-limit cases are intentionally accepted.
Model-generation reliability is a separate experiment; parser-case counts are not model success rates.
