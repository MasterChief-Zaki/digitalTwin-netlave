# netLave Digital Twin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or superpowers:subagent-driven-development) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A demonstrable, physics-informed simulation of a self-powered, TSE-irrigated forest in Egypt. One deterministic Python engine is the physical authority; a Next.js dashboard and an interactive 3D forest display its snapshots. An operator can inject a filter fault or a low-energy event, watch a physically justified control denial, and run an honest 14-day fixed-timer versus smart-hysteresis comparison.

**Spec:** `TSE_Digital_Twin_Implementation_Plan_v5.md` (Execution Plan V5.0, 23 October 2026). Section numbers below (§) refer to it. Where this plan and the spec disagree, the spec wins unless a ruling below says why not.

**Architecture:** FastAPI (one process, one worker, one `threading.Lock`) holds one in-memory run. `engine.step(state, cfg, inputs)` advances 60 s in the causal order of §6 and asserts water, soil and electrical balances every step. The browser reaches it through a Next.js rewrite (`/api/*` → `http://127.0.0.1:8000/*`). Zustand keeps the latest snapshot plus UI-only state (selected zone, play/pause, speed, chart window). React Three Fiber draws the same snapshot and never computes physics.

**Tech stack:** Next.js 16.4.2, React 19.3, TypeScript strict, SCSS modules, three 0.186 + `@react-three/fiber` 9 + `@react-three/drei` 10 (the `netlave` compatibility line), Zustand, Recharts. Python 3.12+ managed with uv, FastAPI, Pydantic 2, pytest, httpx2.

## Global Constraints

- Design language comes from `landing-netlave`: the night palette tokens (`--color-*`), Space Grotesk and IBM Plex Mono, glass-capsule buttons, mono uppercase dash labels (`01 — Label`). No new hex values in components; translucent tints use `color-mix(in srgb, var(--token) N%, transparent)`.
- Mobile-first SCSS with `$tablet-min-width` (768px) and `$desktop-min-width` (1024px).
- three.js loads lazily, in the browser only (`next/dynamic`, `ssr: false`). Only files under `src/components/twin/` import three, r3f or drei. DPR capped at 1.5. No GLTF assets, custom shaders or postprocessing.
- Every displayed physical value comes from a snapshot field or a cumulative backend metric and is labelled **Simulated**.
- JSON is snake_case with units in every dimensional key; `schema_version: "1.0"`, `data_mode: "SIMULATED"`.
- pnpm only. Every commit passes the Husky hook; never `--no-verify`. Backend changes pass `pnpm test:backend` before commit.
- Branches: one epic, `epic/digital-twin`. One branch per task, branched from the epic and merged back with `git merge --no-ff -m "Merge <branch> into the digital twin epic"`. One PR, epic → `main`.
- Commits are atomic plain-English summaries. No `feat:` prefixes. No AI attribution.

## Site constants (§5, synthetic)

| Item                          | Value                                                                                                                                                     |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Zones A / B / C               | 6 / 5 / 4 ha; gravity / gravity / pumped; elevation +2 / +8 / +34 m; emitter head 10 / 9 / 10 m; max 120 / 100 / 24 m³/h                                  |
| Mainlines                     | 350 m / 350 m / 450 m, all 0.20 m, Darcy f = 0.025                                                                                                        |
| Shared gravity manifold (A+B) | 140 m³/h                                                                                                                                                  |
| Reservoir                     | 1,500 m³ capacity, 900 initial, 50 dead; floor +20.5 m, 2.5 m deep at capacity (surface +22.0 m at 900 m³)                                                |
| TSE inflow                    | 60 m³/h daily mean, ±25% diurnal profile peaking 14:00                                                                                                    |
| Hydro                         | 3 m recoverable inlet head, η 0.60 (≈294 W at 60 m³/h)                                                                                                    |
| Solar                         | 8 kWp × 0.75 derate × max(0, sin(π(h−6)/12))^1.2 × cloud factor                                                                                           |
| Battery                       | 15 kWh, 3 kW charge and discharge, η 0.95 each way, cell floor SoC 0.10, pump reserve SoC 0.20                                                            |
| Loads                         | Pump ≤ 3,000 W at 55% wire-to-water; aux 50 W; flush 1,200 W for 5 steps                                                                                  |
| Soil                          | θwp 0.10, θfc 0.22, θsat 0.38; root depth 0.8 m; Kc 0.85; application efficiency 0.90; θon 0.166, θoff 0.198                                              |
| ET0                           | 4.9 mm/day nominal; seeded day-to-day ±10%; distributed over daylight with the solar sine shape                                                           |
| Filter                        | ΔP = 12,000 + 40,000·CI Pa; k = 3.5×10⁻⁴ per filtered m³ (×8 scenario multiplier); flush at CI ≥ 0.60; CI 0.05 after flush; 1.5 m³ and 0.10 kWh per flush |
| Leaching allowance            | 15%, used only for the fixed timer's daily gross depth                                                                                                    |
| Clock                         | `dt_s = 60`, `sim_time_s = step × 60`, simulated day starts at 06:00                                                                                      |

## Rulings on the spec

1. **Repository layout.** The Next.js app lives at the repo root (like `netlave` and `landing-netlave`) and the Python service in `backend/`, instead of `frontend/` + `backend/`. One `package.json`, one Husky hook, and `pnpm` commands from the root. The `backend:*` and `test:backend` scripts call `uv --directory backend …`, so they work on any OS.
2. **Two battery thresholds.** The spec lists both "0.2–1.0 SoC" and a "20% pump reserve". The cells may discharge to 0.10 for the 50 W auxiliary load; the pump may only draw battery energy above 0.20. Otherwise the reserve reserves nothing, and `AUX_POWER_OUTAGE` and `BATTERY_BELOW_RESERVE` collapse into one condition.
3. **Extra reason codes.** The required list has no code for an accepted hysteresis stop or fixed-timer actions, so three are added: `MOISTURE_TARGET_REACHED`, `SCHEDULE_WINDOW_OPEN`, `SCHEDULE_WINDOW_CLOSED`. A pump that would exceed its 3 kW envelope at the computed head is reported as `INSUFFICIENT_HEAD`.
4. **Denial events are per episode.** Every denied step is in that step's `decisions`. The event log records a denial when it starts or its reason changes for that zone, not on every one of the up to 1,440 repeated steps per day; otherwise one night of pump denials pushes every flush and overflow event out of the 1,000-event history.
5. **Snapshot extensions.** Beyond §3's required members, the snapshot carries `environment` (water quality, cloud factor, solids multiplier, inflow availability, ET0), per-zone `control_mode`, `head_available_m` and `head_required_m`, `pump` hydraulics for zone C, and `reservoir.surface_elevation_m`. These make the "uphill proof" and "fault" demo acts visible without the UI inferring physics.
6. **Operator commands are environment or control changes, never state edits.** `set_zone_mode` (AUTO / MANUAL_OPEN / MANUAL_CLOSED), `set_water_quality`, `set_cloud_factor`, `set_solids_multiplier` and `set_inflow_available`. A filter fault is injected by raising the solids-loading multiplier; the clogging itself comes from the engine.

7. **Start margins against chatter.** Gate 3 needs 10 minutes of a zone's flow above the dead volume to START (one minute to KEEP_OPEN), and gate 7 needs 10 minutes of the pump's battery draw above the 20% reserve to START. Without them, valves near an empty reservoir and the pump under low solar flipped between granted and denied every minute.
8. **No preemption.** Requests are ranked open valves first, then water stress, then zone ID. Ranking by stress alone made zones A and B take the shared manifold from each other every few minutes.
9. **Low-solar preset at 24% SoC.** The spec suggests "around 0.21"; at 0.21 the pump is denied on the first step, and at 0.24 it visibly runs about 13 minutes before the reserve denies it.
10. **Python uses uv.** `backend/pyproject.toml` and `backend/uv.lock` replace pip and `requirements.txt`; the pnpm scripts call `uv --directory backend …`.
11. **The demo runs a production build.** Production React redraws the dashboard several times faster than development mode, and the charts redraw at most once a second because Recharts costs tens of milliseconds per render.

## Review Focus

1. **Accounting:** every step closes the reservoir, soil and bus/cell balances with a mixed abs/rel tolerance, and a failure raises with step, account, lhs/rhs.
2. **Concurrency and idempotency:** a retried `/advance` returns the cached reply; a second client on the same `expected_step` gets 409; a request from a previous `run_generation` never mutates the new run.
3. **No fabricated outcomes:** presets only set initial conditions; denials, flushes, recoveries and A/B numbers come from the engine.
4. **Frontend single-flight:** while playing, exactly one `/advance` is in flight; pause stops future requests; a 409 pauses and refetches `/state`.
5. **3D:** one canvas, no allocation in `useFrame`, no physics in the frame loop; the scene still renders the dashboard if WebGL is unavailable.

---

### Task 0: Epic branch and PR

- [ ] `git switch -c epic/digital-twin docs/add-agent-md`, commit this plan (`Add the plan for the digital twin`), push, open a **draft** PR titled `Build the netLave digital twin` with the task branches as a checklist. Until #1 and #2 are merged, the PR targets `docs/add-agent-md`.

### Task 1: Starter cleanup and design tokens — `chore/remove-starter-content`, `design/design-tokens`

- [ ] Remove the create-next-app page, CSS and `public/*.svg`; set the page metadata to `netLave Digital Twin`.
- [ ] Port `landing-netlave/src/styles/{_tokens,_breakpoints}.scss`, `buttons.module.scss`, `layout.module.scss` and `src/app/globals.scss`, plus the Space Grotesk and IBM Plex Mono fonts in `layout.tsx`. Add `pnpm add -D sass`.
- Checks: `pnpm typecheck && pnpm lint && pnpm lint:styles && pnpm format:check && pnpm build`.

### Task 2: Simulation contract — `feature/simulation-contract`

**Produces:** `backend/schemas.py` (Pydantic models of §3 plus rulings 5–6, request payloads, `ConflictError` envelope), `backend/config.py` (one frozen `SiteConfig` with every constant above), `src/types/simulation.ts` (the same shapes), `src/fixtures/initial-snapshot.json` (§3 initial fixture), the `/api` rewrite in `next.config.ts`, `backend/pyproject.toml` and `backend/uv.lock` (uv-locked dependencies) and the `backend:*` / `test:backend` scripts.

- [ ] Tests first: `test_contract.py` validates the fixture with Pydantic and asserts every reason code string.
- Checks: `pnpm test:backend` plus the frontend checks.

### Task 3: Water and soil engine — `feature/water-and-soil-engine`

**Produces:** `twin/state.py`, `twin/inputs.py`, `twin/engine.py`, `models/water_soil.py`, `GET /state`, `POST /advance` (with `expected_step` and `run_generation` checks).

- [ ] Tests first: C1 water conservation over 1,000 steps with overflow, C2 soil conservation in wet and dry cycles, P4 overflow at capacity, D1 deterministic replay, S1 bounds for an empty reservoir and zero inflow.

### Task 4: Hydraulics, energy and control — `feature/hydraulics-and-energy`

**Produces:** `models/hydraulics.py`, `models/energy.py`, `control/policy.py` (`SMART_HYSTERESIS`, `FIXED_TIMER`), `control/safety.py` (the seven gates of §7, in order).

- [ ] Tests first: §5 sanity checks (294 W hydro, ≈2.8 kW pump for zone C, 625 m³/day net ET), C3 electrical conservation for charge, discharge, full battery and shortage, P1 pump denial with zero delivery and an event, manifold contention.

### Task 5: Filtration, events and run control — `feature/filtration-and-events`

**Produces:** `models/filtration.py`, the event ledger, `POST /command`, `POST /reset`, `GET /events`, `GET /scenarios`, the idempotency ledger (256 entries) and `scenarios/presets.py` (`baseline`, `clogged_filter`, `low_solar`, `tse_interrupt`).

- [ ] Tests first: P2 zone B denied for head while A runs, P3 flush exclusive for five steps with 1.5 m³ and 0.10 kWh booked once, A1 idempotent retry, A2 concurrent same-step clients, A3 stale generation after reset, water-quality HOLD denial.

### Task 6: Dashboard — `feature/dashboard`

**Produces:** `src/services/api.ts`, `src/store/useTwinStore.ts`, `src/components/dashboard/{StatusBar,Kpis,ZoneControls,Charts,Events}.tsx`. Single-flight play loop, speed presets, scenario selector, zone selection and commands, ring-buffered chart series, event feed. Renders the fixture before the backend answers.

- Checks: frontend checks, then a browser run against both servers: advance, pause, a 409 from a second tab, a pump denial visible in the zone panel and the feed.

### Task 7: 3D twin — `feature/twin-scene`

**Produces:** `src/components/twin/{LazyTwin,TwinCanvas,Forest,Infrastructure}.tsx`; adds three, r3f, drei and `@react-three/eslint-plugin`. Three terraces, ~150 instanced trees tinted by zone moisture, reservoir water scaled by volume, inlet turbine, solar array, filter and pump, gravity and pumped pipes coloured by flow, click-to-select zones, active / idle / fault tints.

- Checks: frontend checks, one canvas, ≥30 FPS on the demo machine, zone click selects the same zone as the dashboard.

### Task 8: A/B comparison — `feature/ab-comparison`

**Produces:** `scenarios/comparison.py`, `POST /compare`, `src/components/dashboard/Compare.tsx`. Same inputs, hardware, initial state and safety; only the request policy differs.

- [ ] Tests first: X1 identical input digest and coherent metrics over 14 days, X2 30-day soak with no invalid state or counter reversal, a benchmark under 5 s.

### Task 9: README and startup — `docs/readme-and-startup`

- [ ] README: what it is and is not, one-command and two-terminal startup, the assumptions table (value, unit, status, source), the three §5 sanity checks, limitations, the eight-minute demo script and the measured A/B benchmark. `pnpm demo` starts both servers.
