# Water-only scheduler validation

**Decision: no automatic default-policy promotion.**

Recorded trial commit: `dc6d9d77620dc5d42175a1777a35438c46c07680`.
Working tree dirty during trials: `False`.
80 paired trials; 11/12 service endpoints pass.

These are simulated model results, not field measurements. See the paired
protocol and design/deployment boundary; a service PASS is not hardware approval.

| Scenario       | Profile | Zone | Mean extra ET deficit (mm) | Upper bound (mm) | Result       |
| -------------- | ------- | ---- | -------------------------: | ---------------: | ------------ |
| baseline       | nominal | A    |                   0.000128 |         0.000391 | PASS         |
| baseline       | nominal | B    |                  -0.031315 |        -0.016088 | PASS         |
| baseline       | nominal | C    |                  -0.297443 |        -0.227196 | PASS         |
| clogged_filter | nominal | A    |                  -0.000782 |         0.001532 | PASS         |
| clogged_filter | nominal | B    |                  -0.004357 |         0.000061 | PASS         |
| clogged_filter | nominal | C    |                   0.053364 |         0.101840 | INCONCLUSIVE |
| low_solar      | nominal | A    |                  -0.005341 |         0.000241 | PASS         |
| low_solar      | nominal | B    |                  -0.044655 |        -0.030103 | PASS         |
| low_solar      | nominal | C    |                  -2.013729 |        -1.595722 | PASS         |
| tse_interrupt  | nominal | A    |                   0.000128 |         0.000391 | PASS         |
| tse_interrupt  | nominal | B    |                  -0.031315 |        -0.016088 | PASS         |
| tse_interrupt  | nominal | C    |                  -0.297443 |        -0.227196 | PASS         |

The JSON companion preserves protocol/config/runtime/source provenance, paired
effect intervals, residuals and the SHA-256 of the raw artifact. It does not
rewrite trial provenance to the reporting commit. Raw trials remain in
ignored artifacts/rca/. No threshold relaxation or policy promotion is implied.
