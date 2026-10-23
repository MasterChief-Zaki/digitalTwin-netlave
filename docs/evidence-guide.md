# Reading the evidence without overclaiming

A good comparison asks whether the system used fewer resources **while still serving irrigation adequately**. Lower delivery can also mean the trees were under-served or the run ended with drier soil. This guide explains how to distinguish those cases in the prototype.

All results discussed here are synthetic model evidence. They are not field measurements, hardware acceptance or proof of forest health.

## Three different questions

| Evidence                             | Question it answers                                                                   | What it does not establish                                              |
| ------------------------------------ | ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| Historical baseline, seed 7, 14 days | How did fixed timer and hysteresis behave from the preset, including startup?         | Steady-state savings, candidate scheduler release or field performance. |
| Dashboard single-seed experiment     | What happens for this chosen preset and horizon, with or without common warm-up?      | Statistical release acceptance or a measured installation outcome.      |
| Held-out resource-aware trials       | Does the candidate preserve the declared service level across the chosen test matrix? | Real-world calibration, compliance or guaranteed statistical power.     |

Do not relabel one as another. A matching seed or a larger number of simulated days does not make a diagnostic into release evidence.

## The historical baseline

The published startup-inclusive baseline compares the same site, initial state, seed and inputs. Only the request policy changes. The fixed timer is already sized using ET demand, application efficiency and a leaching allowance; it is not an intentionally wasteful straw man.

| Metric over 14 simulated days     | Fixed timer | Smart hysteresis |
| --------------------------------- | ----------: | ---------------: |
| Irrigation delivered              |   11,404 m³ |        11,411 m³ |
| ET deficit                        |     0.42 mm |          0.56 mm |
| Deep percolation                  |        0 m³ |             0 m³ |
| Overflow / diversion              |    8,245 m³ |         8,139 m³ |
| Pump energy                       |     360 kWh |          399 kWh |
| Unserved admitted electrical load |       0 kWh |            0 kWh |

These are rounded historical results from baseline, seed 7, 14 days—not a new run performed while editing this guide. Smart hysteresis did not save water: delivery was slightly higher, with more pumping and a slightly larger deficit. The shared network's queueing behavior matters.

The historical benchmark reported about 2.9 seconds on the development laptop for two 20,160-step runs. That is a machine/runtime timing observation, not a guaranteed throughput. The test suite retains a five-second comparison gate; measure it without another heavy batch consuming the machine.

## What to read beside water delivery

### ET service and deficit

ET means evapotranspiration. The model compares potential ET demand with actual ET supplied from each soil bucket. Its deficit and service ratio are irrigation-adequacy proxies, not measured tree condition.

Read each zone, especially uphill C. A site-wide average can hide an under-served zone behind well-served gravity zones.

### Starting and ending stocks

A controller can deliver less irrigation by drawing down soil water. It can also appear to use less stored electrical energy simply because the ending battery state is lower.

Reports therefore include initial/final root-zone storage, reservoir volume and battery energy, plus soil-stock-adjusted delivery. Keep those values with the resource totals. Do not compare raw delivery while omitting the resulting stock difference.

### Admitted-load electrical autonomy

The safety resolver can refuse an unpowerable pump request before dispatch. Electrical autonomy then describes the loads that were admitted—not the hypothetical energy needed to satisfy every irrigation request.

A high autonomy value with poor C service is possible. Read ET service, denied/deferred requests and pump behavior alongside it. A 100% score does not prove the real forest can power itself.

### Repeated requests and deferrals

A denied request may repeat over many simulation steps. Its accumulated requested-undelivered volume is not a unique measured crop shortage. The model separately reports ET deficit and time below the moisture trigger.

Scheduler deferrals and safety denials are also different. A candidate may hold a request upstream of safety; the reason totals and session/pause/resume counts help explain that behavior.

## What common warm-up changes

In `MATCHED_OPERATION`, the model runs a common fixed-timer preconditioning period, clones the resulting physical state for each policy, and resets measured accounts without resetting the clock. The dashboard uses 10 days; the API also allows declared 5/20-day sensitivities.

The day-one TSE fault is disabled during preconditioning and moved into the scored window. It is not silently removed from the comparison.

This reduces one source of startup differences. It does not prove that the model has converged to a real equilibrium or that a single seed is enough to establish savings.

## The held-out scheduler decision

The resource-aware candidate is compared with unchanged smart hysteresis under the [rca-paired-v2 protocol](rca/paired-protocol.md):

- Common 10-day fixed-timer warm-up, then 30 measured days.
- Seeds 100–119.
- Four presets and synthetic nominal, shifted-sun, cloud-pulse and three-day-dark profiles in the combined study.
- Current generation only; the scheduler cannot inspect future realized inputs or profile labels.
- Paired bootstrap bounds with 20,000 resamples, a fixed random seed and adjustment across declared service endpoints.

Here, an **endpoint** is a declared zone/scenario/profile service check, not an API route. A paired trial runs the reference and candidate on matching inputs and starting stocks.

Service non-inferiority means the candidate's extra ET deficit/degradation stays within the declared bounds. Every declared zone must meet both the ≤0.10 mm deficit bound and ≤0.005 fractional-degradation bound. The release summary also requires the exact distinct seed set 100–119 and 30 measured days; any arbitrary set of 20 seeds is not equivalent. A mean that looks good is not enough if its upper bound does not meet the rule.

| Published study                                                             | Paired trials | Service checks                            | Decision        |
| --------------------------------------------------------------------------- | ------------: | ----------------------------------------- | --------------- |
| [Water-only, nominal profile](rca/validation/water-scheduler-validation.md) |            80 | 11/12 pass; clogged-filter C inconclusive | Do not promote. |
| [Combined water and energy](rca/validation/combined-validation.md)          |           320 | 41/48 pass; seven C checks inconclusive   | Do not promote. |

**Smart hysteresis remains the default.** Resource-aware scheduling is available to inspect, not automatically promoted by a lower water total or a passing subset of checks. INCONCLUSIVE means the declared evidence did not establish acceptance; it is not a success label.

The published reports pin trial commit `dc6d9d77620dc5d42175a1777a35438c46c07680` and retain configuration/runtime details and raw-result hashes. Preserve that provenance even when website or documentation commits become newer. Do not tune thresholds or extend seeds after seeing results and then describe the old protocol as unchanged.

## Synthetic design studies are not a shopping list

The [design study and deployment boundary](rca/validation/design-and-deployment.md) examines six hardware configurations at seed 7 over 30 days. Lower pump rated flow improves one power margin; more solar helps some deficits; more battery cannot cure a sustained generation shortfall. None of those isolated improvements establishes the full service target or replaces the default hardware assumptions.

A larger pipe can improve head without reaching the proposed design margin. A less-loaded filter can still interrupt irrigation during an exclusive backflush. Surplus TSE needs an approved inflow/outlet plan, not deliberate overwatering or a claim that bigger storage fixes everything.

Startup and 5/20-day warm-up sensitivities remain diagnostics. They do not establish independent-policy equilibrium initialization, field calibration or forest survival.

## Reproduce deliberately

Run these from the repository root. They write artifacts under the ignored `artifacts/rca/` directory; they do not advance your dashboard's live run.

```bash
# Original startup/fault reference matrix
uv --directory backend run python -m scenarios.rca_trials --output ../artifacts/rca/reference.json

# Combined held-out resource-aware comparison
uv --directory backend run python -m scenarios.paired_evaluation --output ../artifacts/rca/combined-validation.json --require-clean

# Water-only ablation, with the nominal profile
uv --directory backend run python -m scenarios.paired_evaluation --output ../artifacts/rca/water-scheduler-validation.json --profiles nominal --water-only --require-clean

# Single-seed hardware sizing study
uv --directory backend run python -m scenarios.design_study --output ../artifacts/rca/design-study.json
```

Use `--require-clean` for reference exports you intend to publish. Dirty diagnostic runs must stay labelled. Full sweeps can take substantially longer than a dashboard comparison; do not run them beside timing benchmarks. Read the [formal evaluation specification](rca/evaluation-spec.md) and [paired protocol](rca/paired-protocol.md) before treating an export as release evidence.

For a fast diagnostic only:

```bash
uv --directory backend run python -m scenarios.paired_evaluation --profiles nominal --seeds 100 101 --horizon-days 1 --output ../artifacts/rca/diagnostic.json
```

Two seeds and one day cannot pass the release rule. Do not publish that small run as a replacement for the held-out matrix.

## Before publishing a result

Include the preset, policy, seed(s), horizon, warm-up, input/initial-state matching, source revision and relevant runtime/configuration. Keep per-zone service and ending stocks beside water and energy totals. State that the result is simulated.

Software tests show that balances, contracts and scenarios behave as specified. They do not replace measured pump curves, irradiance/battery performance, water-quality records, soil/species data, agronomic agreement or current reuse approvals. That work remains outside the prototype's validated scope.
