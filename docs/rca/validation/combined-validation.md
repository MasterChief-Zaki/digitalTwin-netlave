# Combined water and energy validation

**Decision: no automatic default-policy promotion.**

Recorded trial commit: `dc6d9d77620dc5d42175a1777a35438c46c07680`.
Working tree dirty during trials: `False`.
320 paired trials; 41/48 service endpoints pass.

These are simulated model results, not field measurements. See the paired
protocol and design/deployment boundary; a service PASS is not hardware approval.

| Scenario       | Profile        | Zone | Mean extra ET deficit (mm) | Upper bound (mm) | Result       |
| -------------- | -------------- | ---- | -------------------------: | ---------------: | ------------ |
| baseline       | cloud_pulses   | A    |                   0.002455 |         0.010494 | PASS         |
| baseline       | cloud_pulses   | B    |                  -0.047847 |        -0.032470 | PASS         |
| baseline       | cloud_pulses   | C    |                  -2.380507 |        -1.832746 | PASS         |
| baseline       | nominal        | A    |                   0.000445 |         0.001542 | PASS         |
| baseline       | nominal        | B    |                  -0.031258 |        -0.014276 | PASS         |
| baseline       | nominal        | C    |                  -0.262160 |        -0.160690 | PASS         |
| baseline       | shifted_sun    | A    |                   0.003952 |         0.016872 | PASS         |
| baseline       | shifted_sun    | B    |                  -0.031383 |        -0.014105 | PASS         |
| baseline       | shifted_sun    | C    |                  -0.123439 |        -0.049269 | PASS         |
| baseline       | three_day_dark | A    |                   0.008679 |         0.027334 | PASS         |
| baseline       | three_day_dark | B    |                  -0.031251 |        -0.014476 | PASS         |
| baseline       | three_day_dark | C    |                   1.109175 |         1.308633 | INCONCLUSIVE |
| clogged_filter | cloud_pulses   | A    |                   0.002301 |         0.007491 | PASS         |
| clogged_filter | cloud_pulses   | B    |                  -0.000830 |         0.000257 | PASS         |
| clogged_filter | cloud_pulses   | C    |                   0.917706 |         1.436862 | INCONCLUSIVE |
| clogged_filter | nominal        | A    |                  -0.000527 |         0.002163 | PASS         |
| clogged_filter | nominal        | B    |                  -0.004359 |         0.000085 | PASS         |
| clogged_filter | nominal        | C    |                   0.072343 |         0.137787 | INCONCLUSIVE |
| clogged_filter | shifted_sun    | A    |                   0.000750 |         0.003730 | PASS         |
| clogged_filter | shifted_sun    | B    |                  -0.004061 |         0.000111 | PASS         |
| clogged_filter | shifted_sun    | C    |                   0.079840 |         0.160493 | INCONCLUSIVE |
| clogged_filter | three_day_dark | A    |                   0.001110 |         0.003407 | PASS         |
| clogged_filter | three_day_dark | B    |                  -0.002862 |         0.000274 | PASS         |
| clogged_filter | three_day_dark | C    |                   2.970089 |         3.650174 | INCONCLUSIVE |
| low_solar      | cloud_pulses   | A    |                   0.050117 |         0.092043 | PASS         |
| low_solar      | cloud_pulses   | B    |                  -0.058702 |        -0.025172 | PASS         |
| low_solar      | cloud_pulses   | C    |                   0.072641 |         0.191802 | INCONCLUSIVE |
| low_solar      | nominal        | A    |                   0.004228 |         0.028363 | PASS         |
| low_solar      | nominal        | B    |                  -0.044703 |        -0.028288 | PASS         |
| low_solar      | nominal        | C    |                  -1.754255 |        -1.197911 | PASS         |
| low_solar      | shifted_sun    | A    |                   0.003103 |         0.023236 | PASS         |
| low_solar      | shifted_sun    | B    |                  -0.047575 |        -0.030135 | PASS         |
| low_solar      | shifted_sun    | C    |                  -1.696156 |        -1.176910 | PASS         |
| low_solar      | three_day_dark | A    |                   0.036824 |         0.084161 | PASS         |
| low_solar      | three_day_dark | B    |                  -0.057369 |        -0.026192 | PASS         |
| low_solar      | three_day_dark | C    |                  -0.468026 |        -0.181984 | PASS         |
| tse_interrupt  | cloud_pulses   | A    |                   0.002455 |         0.010494 | PASS         |
| tse_interrupt  | cloud_pulses   | B    |                  -0.047847 |        -0.032470 | PASS         |
| tse_interrupt  | cloud_pulses   | C    |                  -2.380507 |        -1.832746 | PASS         |
| tse_interrupt  | nominal        | A    |                   0.000445 |         0.001542 | PASS         |
| tse_interrupt  | nominal        | B    |                  -0.031258 |        -0.014276 | PASS         |
| tse_interrupt  | nominal        | C    |                  -0.262160 |        -0.160690 | PASS         |
| tse_interrupt  | shifted_sun    | A    |                   0.003952 |         0.016872 | PASS         |
| tse_interrupt  | shifted_sun    | B    |                  -0.031383 |        -0.014105 | PASS         |
| tse_interrupt  | shifted_sun    | C    |                  -0.123439 |        -0.049269 | PASS         |
| tse_interrupt  | three_day_dark | A    |                   0.008679 |         0.027334 | PASS         |
| tse_interrupt  | three_day_dark | B    |                  -0.031251 |        -0.014476 | PASS         |
| tse_interrupt  | three_day_dark | C    |                   1.109175 |         1.308633 | INCONCLUSIVE |

The JSON companion preserves protocol/config/runtime/source provenance, paired
effect intervals, residuals and the SHA-256 of the raw artifact. It does not
rewrite trial provenance to the reporting commit. Raw trials remain in
ignored artifacts/rca/. No threshold relaxation or policy promotion is implied.
