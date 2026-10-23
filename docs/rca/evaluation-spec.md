# RCA evaluation specification

## Status and scope

Protocol **`rca-startup-v1`** establishes the unchanged controller reference
before resource-aware scheduling. Its executable definitions are in
`backend/scenarios/evaluation.py` and its headless exporter is
`backend/scenarios/rca_trials.py`. It implements startup/fault trials only;
per-zone service exports now accompany its results. Matched operation and
confidence intervals use the separate [paired protocol](paired-protocol.md).
The [validation reports](validation/combined-validation.md) record the delivered
scheduler's limits; this startup runner never implies steady-operation acceptance.

Reference behavior is pinned to Git commit
`4ae12eb774e422679c04e0d94c661351ae879747` on the digital twin epic.
`backend/tests/fixtures/rca-reference.json` is computed from that commit's backend,
not transcribed from the rounded PDF figures. Its runtime and configuration
provenance travel with the fixture.

`SMART_HYSTERESIS` remains the default. The experimental `SMART_RESOURCE_AWARE` policy
must remain opt-in until its separate water-scheduler and combined water/energy
validation reports pass the pre-registered gates below. No physical safety gate,
per-step conservation assertion or original controller is weakened to achieve a
comparison target.

All outputs are **synthetic simulation results, not field measurements**. ET
adequacy is not proof of tree health, salinity control or regulatory compliance.

## Reference trial protocol

- Four presets: baseline, clogged filter, low solar and TSE interruption.
- Both unchanged policies: `FIXED_TIMER` and `SMART_HYSTERESIS`.
- Reference seeds: 3, 7 and 11; horizons: 14 and 30 elapsed days.
- No warm-up and no discarded steps. Each measurement starts at step 0 and ends
  at `horizon_days × STEPS_PER_DAY`; steps use half-open intervals `[start, end)`.
- Simulated days run 06:00 to 06:00; `DT_S = 60`, not wall-clock execution time.
- Presets retain their documented demo initial states and day-one faults. The TSE
  outage remains steps `[30, 390)`; it cannot disappear into a warm-up discard.
- Each policy owns a new scenario state. Matching environmental input and
  policy-neutral initial-state digests are asserted, not just displayed.
- Initial and final root-zone, reservoir and battery stocks are exported.
- Minima include the initial state and every end-step state.
- No result is described as a controller savings claim by this reference runner.

Run from the repository root:

```bash
uv --directory backend run python -m scenarios.rca_trials --output ../artifacts/rca/reference.json
```

For a short diagnostic run:

```bash
uv --directory backend run python -m scenarios.rca_trials --output ../artifacts/rca/smoke.json --scenarios baseline low_solar --seeds 7 --horizons-days 1
```

Paths passed to `--output` are relative to `backend/` because of `uv --directory`.
For published artifacts add `--require-clean`; a dirty tree is rejected. Without
that flag, diagnostic artifacts explicitly record `working_tree_dirty: true`.
Artifacts record the executing Git commit, reference commit, backend source
hash, full configuration and digest, protocol version/spec hash, Python runtime
and uv lock hash. Text hashes canonicalize CRLF to LF so Windows Git checkout
line endings do not masquerade as code or dependency changes. Source/configuration hashes do not substitute for the commit.
The source hash includes backend tests and excludes hidden environment/cache
directories. The sweep fails if source bytes change while it is executing.

## Numerical reproducibility

1. **Pinned-runtime replay:** exact equality of physical results and digests in
   the same runtime/source/configuration. Runtime/provenance fields and elapsed
   wall time are not physical results. The trial runner omits wall time entirely.
2. **Historical fixture checks:** strings, integers and booleans match exactly.
   Floats use field units: m³ absolute tolerance `1e-6`, kWh absolute tolerance
   `1e-6`, mm/kWh-per-m³/moisture/fractions absolute tolerance `1e-12`; relative tolerance
   `1e-9`. The test maps every historical numeric field explicitly to a unit.
3. **Cumulative water closure:** `abs_tol=1e-6 m³`, `rel_tol=1e-9`.
4. **Cumulative bus/cell closure:** `abs_tol=1e-6 kWh`, `rel_tol=1e-9`.
5. These are export checks in addition to the unchanged engine assertions.
   Nonfinite values are rejected; strict JSON serialization forbids NaN/Infinity.

Do not compare PDF-rounded figures with these machine-precision tolerances.
Changing a tolerance or evaluation definition requires a protocol revision and
rerunning the reference tests; it is not a controller tuning knob.

## Storage, application efficiency and accounts

Soil storage means the current engine's **root-zone bucket**, not a full soil
profile:

```text
S_zone_m3 = theta_m3_m3 × area_m2 × configured_root_depth_m
Delta_S_m3 = S_final_m3 − S_initial_m3
```

P0 keeps application efficiency fixed at `cfg.soil.application_efficiency`
(currently 0.90), independent of pressure/flow. A later flow-dependent model
requires a new protocol and cannot silently reuse the fixed-efficiency metric.

```text
soil_stock_adjusted_delivery_m3 = delivered_m3 − Delta_S_m3 / efficiency
```

Accumulation is removed; depletion is added back. This measure is not sufficient
for an efficiency claim: different actual ET or drainage still changes it.
Reservoir and battery stock changes remain separate, not mixed into this metric.

The runner asserts and exports residuals for:

```text
Delta_V = inflow − irrigation − flush − overflow − other_diversion
Delta_S = irrigation − application_loss − actual_ET − deep_percolation
bus_supply = hydro + solar + battery_discharge + unserved
bus_demand = admitted_loads + battery_charge + curtailment
Delta_E_cells = battery_charge − battery_discharge − battery_losses
```

These energy terms are bus-side integrals except the explicitly named cell
stock change and losses. `required_electrical_energy_j` means admitted loads;
rejected pump demand does not enter electrical autonomy.

## Metric conventions

These pre-registered definitions are exported by the schema 1.1 service contract:

- Below-trigger time integrates `DT_S` for each step whose **pre-step** moisture
  is strictly below the **entry** threshold (`theta_on`, currently 0.166). Equality
  is not below. The exit/target threshold is not used for this duration.
- ET-weighted stress is a separate integral of
  `potential_ET_step − actual_ET_step`; daylight/ET weighting never replaces
  elapsed below-trigger minutes.
- Denied zone-minutes integrate denied water-request steps, not deduplicated
  denial events. Stop/keep-closed decisions are not denied demand.
- A future latched demand has mutually exclusive per-step outcomes: scheduled
  delivery, scheduling deferral, or safety denial. A paused session retains its
  session identity/latch; pause time is deferral, not a new request/session.
- Requested-undelivered volume is a repeated-request volume integral, not unmet
  crop demand. It remains separately labelled.
- Equivalent full cycles are **cell-side discharged energy / nominal capacity**:
  `bus_discharge_j / discharge_efficiency / capacity_j`. Charging is not counted
  again. Battery losses are the engine's independent loss integral and do not
  depend on this cycle-counting convention.

## Pre-registered controller evaluation gates

The following are model-only engineering targets, not agronomic field limits.
They are fixed before implementation of the new scheduler:

- Primary regression comparator: unchanged `SMART_HYSTERESIS`. Fixed timer is a
  second benchmark, with its results and service shown separately.
- For each zone and scenario over a 30-day measured window, additional ET deficit
  must be at most **0.10 mm** and ET-service degradation at most **0.005** of the
  potential ET (0.5 percentage points). Both limits apply independently.
- Startup is separate: compare the first five days against unchanged hysteresis
  with the same 0.10 mm/0.005 degradation limits; report time to complete the
  initial refill and test the report's five-day baseline refill target.
- Reference trial seeds are not validation evidence. Use 20 paired validation
  seeds `100..119`, not used for tuning, and a held-out environmental-profile
  suite. Evaluate each zone/scenario, not just site-wide averages.
- Report paired absolute effects, relative effects with nonzero denominators,
  confidence bounds and sign counts. Use one-sided non-inferiority bounds with
  family-wise 5% error control across the declared zone/scenario endpoints.
- Confidence-interval construction and the held-out profiles must be fixed in
  the next protocol before tuning. No acceptance claim is enabled by this
  reference runner. An interval exceeding the margin is inconclusive/fail, never
  a pass based solely on the mean or an 8-of-10 sign count.
- No sequential seed extension until a predeclared extension rule exists. No
  post-result margin changes; justified changes require a new protocol version.

Primary steady-operation comparisons will precondition under unchanged fixed
timer control, clone a common physical state, initialize policy memory
consistently, then measure 30 days. Transient faults must occur inside the scored
window. Independent-policy warm-up is a separately labelled sensitivity study,
with divergent stocks reported; it is not the primary matched-state experiment.
Warm-up sensitivity uses 5, 10 and 20 days and reports materially unstable results.
This is implemented under `rca-paired-v2`, not a hidden alteration of the
reference trials. See the recorded warm-up sensitivity diagnostics.

Water scheduling must have bounded sessions, normal minimum run/rest rules,
restart hysteresis, and waiting-time fairness before energy scheduling is added.
Safety always interrupts immediately when necessary. One joint admission rule
requires all applicable inventory/head/manifold/pump/energy budgets to pass.
A documented design floor and per-step actual-filter hydraulic feasibility are
both enforced; neither an 850 m³ constant nor an energy rule overrides hydraulic
failure. Test coincident head/inventory and battery limits, including flush load
and inflow interruption. The scheduler may not access future realized solar
unless an explicit forecast/error model is supplied.

Baseline energy targets remain minimum SoC 35%, losses at most twice timer
losses, and non-inferior zone-C ET at stock-aware comparison. Low-solar scarcity
must remain visible when existing hardware cannot provide the service.

## Corrections to the supplied RCA report

- Zone C rated flow is **24 m³/h = 0.006667 m³/s**, not 0.012 m³/s. The reported
  118.9 W per meter coefficient agrees with the actual configured flow.
- All zones request at startup; the existing manifold already prevents full-flow
  simultaneous delivery to A and B.
- At 850 m³ and clog index 0.56, B has negative head margin and C exceeds 3 kW.
  A universally safe floor cannot be inferred from the 850 m³ example alone.
- Stock adjustment divides by application efficiency and subtracts final-minus-
  initial soil accumulation; `delivered + 0.9 × storage_change` is not used.
- Reservoir overflow cannot be eliminated by scheduling or added buffering when
  inflow persistently exceeds useful demand. No overwatering to meet an overflow
  target, and no receiving-environment or permitting claim from this model.

## Delivery checklist

- [x] Versioned reference definitions and startup/fault runner.
- [x] Commit/runtime/configuration provenance and historical fixture.
- [x] Replay, cumulative closure and headless/live isolation tests.
- [x] Per-zone service contract, synchronized TypeScript/fixtures and dashboard.
- [x] Matched-state warm-up and fixed statistical/held-out protocol.
- [x] Scripted browser service/provenance checks wired into CI (local run passed).
- [x] Opt-in water scheduler and its validation report (not all gates passed).
- [x] Energy-aware scheduling and combined validation report (not all gates passed).
- [ ] Default-policy promotion only after all declared gates pass.
