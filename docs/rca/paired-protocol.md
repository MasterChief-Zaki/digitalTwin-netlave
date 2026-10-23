# Matched policy evaluation — rca-paired-v2

This protocol is fixed before scheduler implementation. The original startup
reference remains available; the following is a separate matched-operation trial.

- Common preconditioning: unchanged fixed timer for 10 days, with 5/20-day and
  zero-warm-up runs as explicitly labelled sensitivities/startup checks.
- TSE interruption is disabled during preconditioning and moved to measured
  steps `[start + 30, start + 390)`. No measured fault is discarded.
- Clone the common soil/reservoir/battery/filter state. Close starting valves and
  clear demand latches consistently; reset measured accounts, not the clock.
- Measure 30 days. Reference is unchanged hysteresis; candidate is opt-in resource
  aware. Input and initial physical digests must match.
- Validation seeds `100..119`. No seed extension or post-result tuning.
- Held-out solar inputs: nominal, two-hour shifted sun, attenuation 0.15 during
  09:00–14:00 and 0.8 otherwise, and attenuation 0.05 on days 2/3/4 of each ten-day
  block. These are synthetic robustness tests, not weather forecasts.
- The scheduler receives only current generation, never the profile identifier
  or future realized inputs. Input selection occurs in the engine.
- Paired bootstrap percentile bounds: 20,000 resamples of paired differences,
  fixed RNG seed 20261023. Bonferroni one-sided alpha `0.05 / endpoint_count`
  across all declared zone/scenario/profile/warm-up service endpoints (both mm
  deficit and fractional degradation). Report mean, std, range and sign counts.
- Pass non-inferiority only when upper bounds are <=0.10 mm and <=0.005 for every
  zone and at least 20 paired seeds were evaluated. Failure to establish this is
  INCONCLUSIVE, not success. Bootstrap bounds are finite-sample exploratory
  model evidence, not a guarantee of power or a field-population inference.
- Raw and soil-stock-adjusted water effects travel with ending stocks. No
  single-seed savings claims and no automatic default-policy promotion.

Run from the root:

```bash
uv --directory backend run python -m scenarios.paired_evaluation --output ../artifacts/rca/paired.json
```

Full profile sweeps may take several minutes. Use `--profiles nominal --seeds
100 101 --horizon-days 1` only for diagnostics; such runs cannot pass release
acceptance. Published results use `--require-clean`.
