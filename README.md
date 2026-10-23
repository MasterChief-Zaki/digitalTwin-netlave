# NetLave Digital Twin

A simulation-driven prototype of treated-wastewater (TSE) forestry irrigation in Egypt, connecting reclaimed water, renewable power and explainable control. Reclaimed effluent arrives continuously, passes a micro-hydro turbine into a reservoir, and feeds three drip zones: two by gravity and one uphill by a solar- and battery-powered pump, through a shared filter that clogs and flushes. An explainable controller asks for water. A safety resolver grants or denies each request against water quality, the filter, reservoir storage, hydraulic head, the shared manifold, instantaneous power and the battery reserve, and gives its reason.

One deterministic Python engine is the physical authority. The Next.js dashboard and the 3D forest only draw the snapshots it returns.

> **Claim limit.** This is a simulation-driven digital twin **prototype** built on synthetic site assumptions. It is not synchronized with, or calibrated against, a real site. Every number is a simulated scenario output, not a measurement. The synthetic water-quality flag is not an Egyptian regulatory compliance test and never permits real-world irrigation.

## Shared brand, content and discovery

All three NetLave sites publish identical `src/content/ground-truth.json` and a server-rendered `/ground-truth` reference. Python remains the physical authority; static references never drive live KPIs. The supplied logo, generated favicons, matching fonts, claim boundaries and SEO/GEO setup are documented in [brand and ground truth](docs/brand-and-ground-truth.md).

Run `pnpm exec node scripts/check-shared-truth.mjs --siblings` with the three repos adjacent. `test_site_ground_truth.py` checks published assumptions, zones and scenario IDs against Python. Set `SITE_URL` to this dashboard's verified production origin at build time for canonicals, social cards and sitemap URLs; no production domain is assumed.

See [development troubleshooting](docs/development-troubleshooting.md) for root configuration, the tracked Fiber Timer patch, supported shadows and browser-extension hydration diagnostics.

## Quick start

Prerequisites: Node.js 24 with pnpm 10, and [uv](https://docs.astral.sh/uv/) (it installs the pinned Python 3.14 itself). Everything runs offline after the first install.

```bash
pnpm install          # JavaScript dependencies and the git hooks
pnpm backend:setup    # Python environment from backend/uv.lock (optional: uv run does it on first start)
pnpm demo             # builds the dashboard, then serves it on http://localhost:3000 with the API on :8000
```

Or use two terminals: `pnpm backend:dev` (FastAPI, one worker, port 8000), then `pnpm dev` (Next.js). The dashboard reaches the API through the Next.js rewrite `/api/*` → `http://127.0.0.1:8000/*`. Before the backend answers, it renders the step-0 fixture.

| Command                                                                | Purpose                                                      |
| ---------------------------------------------------------------------- | ------------------------------------------------------------ |
| `pnpm demo`                                                            | Production build, then both servers; Ctrl+C stops both       |
| `pnpm backend:dev`                                                     | FastAPI simulation on 127.0.0.1:8000                         |
| `pnpm dev`                                                             | Next.js dashboard on localhost:3000                          |
| `pnpm test:backend`                                                    | Backend test suite (conservation, API, scenarios, A/B, soak) |
| `pnpm build`                                                           | Production build of the dashboard                            |
| `pnpm lint`, `pnpm lint:styles`, `pnpm format:check`, `pnpm typecheck` | Frontend checks (also run by the pre-commit hook)            |

## How it fits together

```text
Browser: Next.js 16 + React 19 + TypeScript + SCSS modules
  Dashboard (Recharts)  |  3D forest (React Three Fiber + drei)
                \               /
     Zustand: latest snapshot + UI-only selection, play/pause, speed
                        |  fetch /api/*  (Next.js rewrite)
              FastAPI + Pydantic: one process, one worker, one lock
                        |
        Authoritative in-memory run: engine.step(state, cfg) every 60 s
   reservoir · soil buckets · hydraulics · solar/hydro/battery · filter
            controller request  →  safety gates  →  balances + events
```

- **Clock.** `dt_s = 60`, `sim_time_s = step × 60`. There is no wall-clock time in the physics. The browser advances the run with `POST /advance` and awaits each reply before sending the next, so pause just means "send no more requests".
- **Causal order per step:** inputs → controller requests → filter flush → ranking → safety gates → electrical dispatch → reservoir, soil, filter, events, metrics → balance and bound assertions → step + 1.
- **Every step closes** the reservoir balance (`dV = in − irrigation − flush − overflow`), each soil bucket (`dS = infiltration − actual ET − drainage`), the DC bus (`hydro + solar + discharge + unserved = loads + charge + curtail`) and the battery cells (`dE = charge − discharge − losses`). Any mismatch raises with the step, the account, both sides and the inputs.

### Repository layout

```text
backend/                  Python, managed with uv (pyproject.toml, uv.lock)
  main.py                 routes, lock, idempotency ledger, event ledger
  schemas.py              Pydantic contract (mirrored in src/types/simulation.ts)
  config.py               the one synthetic-parameter table + ASSUMPTIONS
  twin/                   state + snapshot projection, inputs, engine
  models/                 water_soil, hydraulics, energy, filtration
  control/                policy (smart hysteresis, fixed timer, manual), safety gates
  scenarios/              presets, headless A/B comparison
  tests/                  contract, physics, scenarios, API, comparison
src/
  app/                    Next.js App Router page
  components/dashboard/   status bar, KPIs, zones, faults, charts, ledger, events, A/B
  components/twin/        lazily loaded React Three Fiber forest
  store/useTwinStore.ts   Zustand store and the single-flight play loop
  services/api.ts         typed fetch client
  types/simulation.ts     TypeScript mirror of the contract
  fixtures/               step-0 snapshot shared by both sides
```

## API

| Method | Path                 | Input                                                           | Result                                                     |
| ------ | -------------------- | --------------------------------------------------------------- | ---------------------------------------------------------- |
| GET    | `/state`             | –                                                               | full snapshot                                              |
| POST   | `/advance`           | `run_generation`, `expected_step`, `steps` (1–60), `request_id` | new snapshot and new events                                |
| POST   | `/command`           | command + `run_generation`, `expected_step`                     | updated snapshot (no step)                                 |
| POST   | `/reset`             | `scenario_id`, `seed`, `control_policy`                         | step 0, `run_generation` + 1                               |
| GET    | `/events?since_id=N` | last seen event ID                                              | events with `id > N`, `history_truncated`                  |
| GET    | `/scenarios`         | –                                                               | presets and the assumptions table                          |
| POST   | `/compare`           | `scenario_id`, `seed`, `horizon_days` (1–30, default 14)        | fixed timer vs smart hysteresis report; live run untouched |

A stale `run_generation` or `expected_step` gets HTTP 409 with `{error_code: "STEP_CONFLICT", message, current_step, run_generation}`. A retried `/advance` with the same `request_id` and payload returns the cached reply without stepping. The same `request_id` with different arguments gets 409 `IDEMPOTENCY_CONFLICT`. Invalid payloads get 422. Commands (`set_zone_mode`, `set_water_quality`, `set_cloud_factor`, `set_solids_multiplier`, `set_inflow_available`) change control settings or the environment, never physical state.

## Synthetic site assumptions

These are assumptions for a synthetic Egyptian forestry site, not Serapium field measurements. A real deployment replaces them with surveyed head, a measured TSE hydrograph, pipe design, treatment grade, water-quality records, soil laboratory values and species-specific agronomy. The live table is served by `GET /scenarios` from `backend/config.py`.

| Parameter                                              | Value                            | Unit                    | Status  | Source                                         |
| ------------------------------------------------------ | -------------------------------- | ----------------------- | ------- | ---------------------------------------------- |
| Zone areas A / B / C                                   | 6 / 5 / 4                        | ha                      | assumed | Execution plan V5.0, section 5 (synthetic)     |
| Zone feed A / B / C                                    | gravity / gravity / pumped       | -                       | assumed | Execution plan V5.0, section 5 (synthetic)     |
| Zone elevations A / B / C                              | +2 / +8 / +34                    | m                       | assumed | Execution plan V5.0, section 5 (synthetic)     |
| Emitter head A / B / C                                 | 10 / 9 / 10                      | m                       | assumed | Execution plan V5.0, section 5 (synthetic)     |
| Maximum zone flow A / B / C                            | 120 / 100 / 24                   | m3/h                    | assumed | Execution plan V5.0, section 5 (synthetic)     |
| Mainline length / diameter                             | 350, 350, 450 / 0.20             | m                       | assumed | Execution plan V5.0, section 5 (synthetic)     |
| Darcy friction factor (clean mainline)                 | 0.025                            | -                       | assumed | Execution plan V5.0, section 6.3               |
| Shared gravity manifold A+B                            | 140                              | m3/h                    | assumed | Execution plan V5.0, section 5 (synthetic)     |
| Pump electrical limit / wire-to-water efficiency       | 3000 / 0.55                      | W / -                   | assumed | Execution plan V5.0, section 5 (synthetic)     |
| Reservoir capacity / initial / dead                    | 1500 / 900 / 50                  | m3                      | assumed | Execution plan V5.0, section 5 (synthetic)     |
| Reservoir floor / depth at capacity                    | +20.5 / 2.5                      | m                       | assumed | Chosen so the surface is +22 m at 900 m3       |
| Zone start margin above dead volume                    | 10                               | minutes of zone flow    | assumed | Prevents valve chatter near empty              |
| TSE inflow daily mean                                  | 60                               | m3/h                    | assumed | Execution plan V5.0, section 5 (synthetic)     |
| TSE diurnal amplitude / peak hour                      | 25% / 14:00                      | - / h                   | assumed | Synthetic treatment-plant effluent profile     |
| Hydro recoverable inlet head / turbine efficiency      | 3 / 0.60                         | m / -                   | assumed | Execution plan V5.0, section 5 (synthetic)     |
| Solar array / derate                                   | 8 / 0.75                         | kWp / -                 | assumed | Execution plan V5.0, section 5 (synthetic)     |
| Solar profile                                          | sin(pi(h-6)/12)^1.2, 06:00-18:00 | -                       | assumed | Synthetic, not an irradiance forecast          |
| Battery capacity / initial SoC                         | 15 / 0.80                        | kWh / -                 | assumed | Execution plan V5.0, section 5 (synthetic)     |
| Battery cell floor / pump reserve                      | 0.10 / 0.20                      | SoC                     | assumed | Plan ruling 2                                  |
| Pump start margin above the reserve                    | 10                               | minutes of battery draw | assumed | Prevents pump chatter                          |
| Battery charge and discharge limit / efficiency        | 3000 / 0.95                      | W / -                   | assumed | Execution plan V5.0, section 5 (synthetic)     |
| Auxiliary load / flush load                            | 50 / 1200                        | W                       | assumed | Execution plan V5.0, section 5 (synthetic)     |
| Soil wilting point / field capacity / saturation       | 0.10 / 0.22 / 0.38               | m3/m3                   | assumed | Sandy-loam assumption                          |
| Root depth / crop coefficient / application efficiency | 0.8 / 0.85 / 0.90                | m / - / -               | assumed | Execution plan V5.0, section 5 (synthetic)     |
| Irrigation start threshold                             | 0.166                            | m3/m3                   | derived | FAO-56 RAW: fc - 0.45 (fc - wp)                |
| Irrigation stop threshold                              | 0.198                            | m3/m3                   | derived | 0.90 x field capacity                          |
| Reference ET0 (nominal, seeded +/-10% per day)         | 4.9                              | mm/day                  | assumed | Constant fallback of plan section 6.2          |
| Filter pressure drop                                   | 12000 + 40000 x CI               | Pa                      | assumed | Illustrative, plan section 6.5                 |
| Filter loading per filtered m3                         | 3.5e-4                           | CI/m3                   | assumed | Chosen to flush about every 2 days at baseline |
| Flush threshold / water / energy                       | 0.60 / 1.5 / 0.10                | CI / m3 / kWh           | assumed | Execution plan V5.0, section 5 (synthetic)     |
| Leaching allowance (fixed timer only)                  | 15                               | %                       | assumed | Scenario allowance, not salinity control       |
| Water-quality flag                                     | synthetic OK / HOLD / UNKNOWN    | -                       | assumed | Not an Egyptian regulatory compliance test     |

### Three sanity checks

Each is asserted in `backend/tests/test_physics.py`.

1. **Hydro is small.** 60 m³/h through a 3 m recoverable drop at 60% turbine efficiency gives **294 W**, not a 2 kW pump supply. The optimistic 18 m drop would give about 1.77 kW, but that drop is **unverified**.
2. **The uphill pump runs close to its limit.** Zone C at 24 m³/h needs 12 m of static lift from a +22 m reservoir surface, plus 10 m of emitter head, 0.13 m of mainline friction and 1.22 m across a clean filter. That is **23.35 m** of total dynamic head and **2.78 kW** at 55% wire-to-water efficiency. The same 24 m³/h at 28 m would need **3.33 kW**, beyond the 3 kW pump.
3. **Overflow is expected.** At 4.9 mm/day ET0 and Kc 0.85, the 15 ha canopy needs about **625 m³/day** net ET, while 60 m³/h of constant inflow brings **1,440 m³/day**. Reservoir overflow or diversion is part of the design, not a bug.

## Scenarios

Presets only set starting conditions. Every denial, flush and recovery that follows is produced by the engine. Near-threshold values are labelled demo initial conditions, not plausible steady states.

| Preset           | Controlled variation                                                  | What you should see                                                                                      |
| ---------------- | --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `baseline`       | Site defaults; all zones at 0.165 m³/m³, just below the 0.166 trigger | A and C start irrigating; B waits on the shared 140 m³/h manifold (`CONCURRENT_FLOW_LIMIT`)              |
| `clogged_filter` | Solids loading ×8, clog index 0.56, zone B demanding water            | B denied `INSUFFICIENT_HEAD` while A runs; flush at 0.60 (1.5 m³, 0.10 kWh, 5 minutes); then B irrigates |
| `low_solar`      | Cloud factor 0.25, battery at 24%, zone C requesting the pump         | Pump runs about 13 minutes on the battery, then `BATTERY_BELOW_RESERVE` with zero delivered flow         |
| `tse_interrupt`  | No inflow from 06:30 to 12:30                                         | Hydro drops to 0 W; the reservoir draws down                                                             |

Operator faults are also available live: dirty effluent (solids ×8), sandstorm (cloud 0.25), cut TSE inflow, and the HOLD/UNKNOWN quality flag (irrigation fails closed).

### Reason codes

`SOIL_BELOW_THRESHOLD`, `KEEP_OPEN`, `KEEP_CLOSED`, `MANUAL_OVERRIDE_OK`, `MANUAL_STOP_OK`, `WATER_QUALITY_HOLD`, `FLUSH_IN_PROGRESS`, `FILTER_FLUSH_REQUIRED`, `RESERVOIR_LOW`, `INSUFFICIENT_HEAD`, `CONCURRENT_FLOW_LIMIT`, `POWER_DEFICIT`, `BATTERY_BELOW_RESERVE`, `AUX_POWER_OUTAGE`, `FILTER_FLUSH_STARTED`, `FILTER_FLUSH_COMPLETE`, `OVERFLOW_OCCURRING`, `SCENARIO_LOADED`, plus `MOISTURE_TARGET_REACHED`, `SCHEDULE_WINDOW_OPEN`, `SCHEDULE_WINDOW_CLOSED` and `OPERATOR_COMMAND`. The strings are frozen in `backend/tests/test_contract.py`.

## A/B experiment: fixed timer versus smart hysteresis

`POST /compare` (and the dashboard's Experiment panel) runs both controllers headlessly over the same site, weather and inflow series, initial state, seed, water quality and safety gates. Only the request policy differs. Matching input and initial-state digests prove the match. The fixed timer irrigates each zone for a daily window sized from nominal ETc, application efficiency and the 15% leaching allowance. Smart hysteresis starts below 0.166 m³/m³ and stops at 0.198 m³/m³.

Measured on the development laptop, baseline preset, seed 7, 14 days:

| Simulated over 14 days   | Fixed timer | Smart hysteresis |
| ------------------------ | ----------: | ---------------: |
| Irrigation delivered     |   11,404 m³ |        11,411 m³ |
| ET deficit               |     0.42 mm |          0.56 mm |
| Deep percolation         |        0 m³ |             0 m³ |
| Overflow / diversion     |    8,245 m³ |         8,139 m³ |
| Pump energy              |     360 kWh |          399 kWh |
| Unserved electrical load |       0 kWh |            0 kWh |
| Electrical autonomy      |        100% |             100% |

In this synthetic baseline the smart controller does **not** save water: −0.1%, with a slightly higher ET deficit and more pump energy. The fixed timer here is already sized from ET, and the hysteresis controller's zones queue for the shared manifold. Results can favour either controller depending on the assumptions, and this one is reported as computed. Lower water application that stresses the trees would not count as a success. Because every source is renewable, "renewable share" would trivially be 100%, so autonomy is reported with unserved load instead.

**Benchmark:** the 14-day comparison (2 × 20,160 steps) runs in about **2.9 s** on the development laptop, inside the 5 s budget (`test_fourteen_day_comparison_runs_in_under_five_seconds`).

### RCA reference trials

The [RCA evaluation specification](docs/rca/evaluation-spec.md) pins the original
controller reference to a Git commit and defines stock adjustment, cycle counting,
and cumulative account tolerances. Run the full startup/fault matrix (four
scenarios, seeds 3/7/11, 14/30 days, both unchanged policies) from the repo root:

```bash
uv --directory backend run python -m scenarios.rca_trials --output ../artifacts/rca/reference.json
```

Exports contain code/runtime/configuration provenance, initial/final stocks,
computed accounts and closure residuals. Add `--require-clean` when publishing a
reference; dirty-tree diagnostic runs are labelled. This runner does not discard
startup or the day-one TSE outage, and does not establish steady-state savings.
The original controller and default policy remain unchanged. The synchronized
schema 1.1 contract now includes per-zone service and stock diagnostics.

### Connected schematic site view

The polished isometric site view has row-planted instanced trees, routed irrigation,
a reservoir, filter/pump, turbine, solar array and battery/DC bus. Water markers
follow **delivered** flows, while thin energy paths follow the snapshot's power
fields. Scheduler deferrals display as Waiting, not idle. Clicking a terrace or
scene-zone button selects the same dashboard zone.

Schema 1.2 exposes reservoir floor/depth from Python so water elevation and basin
geometry stay consistent. Tree color is only a moisture-stress proxy, not growth
or health. See [rendering connections and tests](docs/rca/schematic-rendering.md).

### Experimental scheduling and validation

Select **Resource aware (experimental, opt-in)** to use bounded joint inventory,
head and battery scheduling. The original `SMART_HYSTERESIS` stays the default:
[water-only validation](docs/rca/validation/water-scheduler-validation.md) and
[combined held-out validation](docs/rca/validation/combined-validation.md) did not
establish service non-inferiority at every endpoint. No savings or field-health
claim follows from lower raw delivery.

The Experiment panel can include the candidate and score matched operation after
a common 10-day fixed-timer warm-up. Faults move into the scored window. Single
seed reports remain diagnostics. Batch commands from the root:

```bash
uv --directory backend run python -m scenarios.paired_evaluation --output ../artifacts/rca/combined-validation.json --require-clean
uv --directory backend run python -m scenarios.paired_evaluation --output ../artifacts/rca/water-scheduler-validation.json --profiles nominal --water-only --require-clean
uv --directory backend run python -m scenarios.design_study --output ../artifacts/rca/design-study.json
```

Full validation uses seeds 100–119, 30 measured days and the documented bootstrap
protocol; the combined sweep includes four solar profiles and can take an hour
on the development laptop. Run it without parallel benchmarks. Computed summary
artifacts and their raw-result hashes are committed under `docs/rca/validation/`.
[Design/deployment boundaries](docs/rca/validation/design-and-deployment.md) explain
which engineering and site decisions remain open.

`pnpm test:browser` builds an isolated production dashboard and launches a private
backend on ports 3100/8100, leaving the demo on 3000/8000 untouched. Install its
browser first with `pnpm exec playwright install chromium`. CI runs backend,
style/lint/type/build and these real-backend browser checks. Browser builds use
`.next-browser/` and `tsconfig.browser.json`; `SIMULATION_BACKEND_URL`,
`NEXT_BUILD_DIRECTORY` and `NEXT_TYPESCRIPT_CONFIG` are server/build settings.

## Tests and acceptance gates

| Gate | Test                                                                                                        |
| ---- | ----------------------------------------------------------------------------------------------------------- |
| C1   | `test_c1_reservoir_water_is_conserved_with_overflow` (plus a per-step reservoir check in the engine)        |
| C2   | `test_c2_soil_water_is_conserved_in_wet_and_dry_cycles`                                                     |
| C3   | `test_c3_bus_and_cell_balances_close` (charging, pump on battery, full battery, shortage)                   |
| S1   | `test_s1_empty_reservoir_without_inflow_stays_in_bounds`                                                    |
| D1   | `test_d1_replay_is_deterministic`                                                                           |
| A1   | `test_a1_retried_advance_returns_the_cached_reply_without_stepping`                                         |
| A2   | `test_a2_two_clients_on_the_same_step_advance_once`                                                         |
| A3   | `test_a3_requests_from_an_old_generation_cannot_touch_the_new_run`                                          |
| P1   | `test_p1_pump_is_denied_at_the_battery_reserve`                                                             |
| P2   | `test_p2_clogged_filter_denies_zone_b_on_head_while_zone_a_runs`                                            |
| P3   | `test_p3_flush_is_exclusive_for_five_steps_and_booked_once`                                                 |
| P4   | `test_p4_full_reservoir_spills_and_stays_at_capacity`                                                       |
| X1   | `test_x1_both_policies_see_identical_inputs_hardware_and_safety`, `test_x1_reports_finite_coherent_metrics` |
| X2   | `test_x2_thirty_day_soak_keeps_valid_state_and_monotonic_counters` (43,200 steps)                           |
| U1   | Manual: the eight-minute demo below, checked in the browser                                                 |

## Eight-minute demo

1. **0:00–1:00 Site.** Show the three terraces, TSE inlet and turbine, reservoir, solar array, filter and pump. Say up front that the parameters are synthetic.
2. **1:00–2:30 Causality.** On `baseline`, press Play at 5 min per tick. Soil moisture, valve state, delivered flow, reservoir volume and energy all move together, and B's card explains the manifold wait.
3. **2:30–4:00 Uphill proof.** Load `low_solar` and select zone C. Show the TDH needed against the pump head the 3 kW limit allows, the pump power, and the battery. Step minute by minute until `BATTERY_BELOW_RESERVE` appears with zero delivered flow. A manual Open is denied for the same reason.
4. **4:00–5:30 Fault.** Load `clogged_filter`. Zone B shows a negative head margin and `INSUFFICIENT_HEAD` while A runs. A few minutes later the flush starts, costs 1.5 m³ and 0.10 kWh, restores the head, and B irrigates.
5. **5:30–7:30 Compare.** Run the 14-day A/B. Walk through water delivered, ET deficit, drainage, overflow and pump energy as simulated scenario outputs, not measured savings.
6. **7:30–8:00 Close.** What is demonstrably viable, and what still needs a site survey, sensors, calibration and permits.

## Design decisions and limitations

- The plan's rulings are recorded in `docs/superpowers/plans/2026-10-23-digital-twin.md`. They cover two battery thresholds, the extra reason codes, denial events per episode, snapshot extensions, start margins against valve and pump chatter, and running valves not being preempted.
- No pump curve: a request gets its full rated flow or none, which is a documented conservative approximation.
- ET0 is a seeded constant-mean daily value spread over daylight hours, not Hargreaves from weather data. Solar is a synthetic sine profile.
- The filter model is solids loading only. Salinity transport, pathogens, tree growth and carbon are not modelled. The leaching allowance is a scenario setting, never proof of salt control.
- There is one in-memory run per server process, with no persistence, telemetry, PLC control or authentication.

**Regulatory boundary.** For a real Egyptian TSE installation, verify the current reuse approval, treatment grade, species authorization, worker protection and monitoring obligations with the competent authorities.

## References

- FAO-56, Chapter 8 (readily available soil water): https://www.fao.org/4/X0490E/x0490e0e.htm
- ISO 20419:2018, treated-wastewater irrigation and clogging: https://committee.iso.org/standard/67959.html
- Egyptian Standards Organization, ES 8174-1/2025: https://www.eos.org.eg/en/standard/14743
- Egyptian Code 501 for treated-wastewater reuse: https://leap.unep.org/en/countries/eg/national-legislation/egyptian-code-no-5012005-use-treated-wastewater-agriculture
- React Three Fiber installation and compatibility: https://r3f.docs.pmnd.rs/getting-started/installation
