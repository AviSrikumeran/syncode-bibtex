# Measured test spectrum

| Category | Expectations met | Median case time (ms) |
| --- | --- | --- |
| regression-valid | 40/40 | 0.0506 |
| regression-invalid | 24/24 | 0.0650 |
| nesting-valid | 8/8 | 0.1353 |
| nesting-invalid | 8/8 | 0.2190 |
| document-size-valid | 4/4 | 2.3887 |
| document-size-invalid | 4/4 | 2.4865 |
| value-length-valid | 5/5 | 0.0403 |
| value-length-invalid | 5/5 | 0.0859 |
| feature-interactions | 48/48 | 0.0958 |
| every-prefix-truncation | 58/58 | 0.1066 |
| semantic-limits-accepted | 5/5 | 0.0680 |
| documented-out-of-scope | 4/4 | 0.0333 |
| lexical-boundary | 2/2 | 0.0321 |
| unicode-content | 0/1 | 0.0473 |

## Scaling observations

| Case | Characters | Accepted | Median ms |
| --- | --- | --- | --- |
| depth-0 | 18 | True | 0.0415 |
| depth-1 | 20 | True | 0.0495 |
| depth-2 | 22 | True | 0.0489 |
| depth-8 | 34 | True | 0.0719 |
| depth-40 | 98 | True | 0.1987 |
| depth-100 | 218 | True | 0.4439 |
| depth-500 | 1018 | True | 2.1209 |
| depth-1000 | 2018 | True | 4.3818 |
| entries-1 | 27 | True | 0.0695 |
| entries-10 | 279 | True | 0.4517 |
| entries-100 | 2979 | True | 4.3258 |
| entries-1000 | 31779 | True | 44.7767 |
| characters-0 | 17 | True | 0.0403 |
| characters-1 | 18 | True | 0.0387 |
| characters-100 | 117 | True | 0.0392 |
| characters-10000 | 10017 | True | 0.0511 |
| characters-100000 | 100017 | True | 0.1467 |

Unexpected outcomes: 1.

- unicode-content/nonbreaking-and-thin-spaces: expected acceptance True; observed False; UnexpectedCharacters.

Timings describe this machine and run, not a controlled performance benchmark.
The largest case tested is not a proven maximum. This is selected boundary coverage, not exhaustive BibTeX conformance.
Out-of-scope rejection does not mean those BibTeX features are invalid. Semantic-limit cases are intentionally accepted.
Model-generation reliability is a separate experiment; parser-case counts are not model success rates.
