# From a request to a snapshot

Python owns the model. The browser owns presentation and user choices. This split prevents the dashboard, chart and 3D scene from inventing different versions of the same reservoir or pump state.

This guide is for changing the implementation or using the local API. For operating the interface, start with the [dashboard guide](dashboard-guide.md).

## The short path

```text
Dashboard controls
  → Zustand request queue
  → typed client calls /api/*
  → Next.js rewrite to FastAPI
  → Python requests, scheduling and safety
  → physical update and balance checks
  → schema 1.2 snapshot
  → one store update for readings, charts and schematic
```

The API has one in-memory run per server process. A single worker and mutation lock coordinate state changes. There is no background physics loop, database, telemetry feed, authentication or hardware output.

## What each part owns

| Part                           | Responsibility                                                        |
| ------------------------------ | --------------------------------------------------------------------- |
| `backend/config.py`            | Synthetic parameters and the served assumption register.              |
| `backend/scenarios/presets.py` | Four demo presets and their initial conditions.                       |
| `backend/twin/inputs.py`       | Reproducible inputs indexed by simulation step and seed.              |
| `backend/control/policy.py`    | Hysteresis/timer demand and per-zone manual requests.                 |
| `backend/control/scheduler.py` | Optional resource-aware shaping of automatic demand.                  |
| `backend/control/safety.py`    | Final delivery gates; no controller can bypass them.                  |
| `backend/models/`              | Reservoir, soil, hydraulics, energy and filter calculations.          |
| `backend/twin/engine.py`       | Step order, physical updates, accounting and assertions.              |
| `backend/twin/state.py`        | State and projection into a snapshot.                                 |
| `backend/main.py`              | API, lock, run generation, retry replies and event IDs.               |
| `src/services/api.ts`          | Typed requests, error handling and snapshot compatibility checks.     |
| `src/store/useTwinStore.ts`    | Latest snapshot, selection, playback and bounded chart/event history. |
| `src/components/twin/`         | Snapshot-driven drawing, not another physical engine.                 |

The shared website JSON is editorial content. It never replaces the latest Python snapshot for readings or live model state.

## What happens in one step?

A step is always 60 simulated seconds, regardless of browser frame rate or playback speed.

1. Evaluate inflow, ET and generation for the current step.
2. Propose each zone's demand using its policy and manual mode.
3. Plan an exclusive filter flush. If selected, the experimental scheduler shapes automatic requests against current resources.
4. Rank the resulting requests deterministically.
5. Resolve quality, filter, storage, head, manifold, pump and electrical limits.
6. Dispatch delivered irrigation and electrical generation/storage/loads.
7. Update reservoir, soil, filter, battery and pump state; record accounts, decisions and event drafts.
8. Assert water/energy balances, finite values and bounds.
9. Increment the step exactly once and return the step result.

The API assigns event IDs and returns a snapshot after these updates. A visual frame only interpolates the drawing. It cannot advance soil water, battery energy or the model clock.

## Schema 1.2 and units

The Python contract in `backend/schemas.py` and its TypeScript mirror in `src/types/simulation.ts` must change together. Field names are snake_case, and dimensional keys include units, such as `volume_m3`, `delivered_flow_m3_s` and `pump_power_w`.

Snapshots identify `schema_version`, `data_mode="SIMULATED"`, step, simulated time, preset, seed and run generation. They contain current component state, decisions, cumulative metrics, per-zone service and site diagnostics.

Schema 1.2 includes reservoir floor and depth so the browser can draw geometry consistently. Per-zone service records actual/potential ET, deficit, root-zone stocks, denials/deferrals and sessions. These are modelled diagnostics, not sensor measurements.

## API endpoints

FastAPI serves the paths below directly. Through the dashboard, add `/api` to the path. With the three-site dev layout, for example, `http://localhost:3002/api/state` proxies to `http://127.0.0.1:8000/state`.

| Method and path          | Request                                                                          | Result                                                                           |
| ------------------------ | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `GET /state`             | None                                                                             | Full snapshot.                                                                   |
| `POST /advance`          | `run_generation`, `expected_step`, `steps` 1–60, `request_id` of 1–64 characters | Updated snapshot, new events, truncation flag and latest event ID.               |
| `POST /command`          | Generation, expected step and a typed command                                    | Updated settings snapshot, without advancing physical time.                      |
| `POST /reset`            | `scenario_id`, nonnegative `seed`, `control_policy`                              | Fresh step 0 and a new generation. Defaults: baseline, seed 7, smart hysteresis. |
| `GET /events?since_id=N` | Last event ID, nonnegative                                                       | Retained newer events, latest ID and history-truncation flag.                    |
| `GET /scenarios`         | None                                                                             | Presets, demo initial conditions and assumption rows.                            |
| `POST /compare`          | Preset, seed, horizon and experiment options                                     | Private headless policy reports; live run untouched.                             |

### Advance safely

Read `/state` before creating an advance request. Use the returned generation and step, not values copied from an old session:

```json
{
  "run_generation": 1,
  "expected_step": 0,
  "steps": 1,
  "request_id": "example-first-minute"
}
```

The generation and step above are illustrative. They are valid only if the current server state matches them.

A retry with the same ID and payload returns the cached response instead of stepping again. The replay ledger is bounded to 256 entries and cleared on reset. Do not treat it as permanent durable idempotency storage.

### Commands change inputs or modes

The command body is a discriminated object under `command`. Supported types are:

| Type                    | Fields                                                   |
| ----------------------- | -------------------------------------------------------- |
| `set_zone_mode`         | `zone_id`: A/B/C; `mode`: AUTO/MANUAL_OPEN/MANUAL_CLOSED |
| `set_water_quality`     | `status`: OK/HOLD/UNKNOWN                                |
| `set_cloud_factor`      | `cloud_factor`: 0–1                                      |
| `set_solids_multiplier` | `multiplier`: 0–20                                       |
| `set_inflow_available`  | `available`: boolean                                     |

Commands do not directly set physical stocks. A manual open can still be denied at the next resolver step. The synthetic water-quality flag is never real-world reuse authorization.

### Comparison options

`POST /compare` accepts:

- `scenario_id`, default baseline.
- `seed`, default 7, nonnegative.
- `horizon_days`, 1–30, default 14.
- `evaluation_mode`: `STARTUP_FAULT` by default or `MATCHED_OPERATION`.
- `warmup_days`: 5, 10 or 20, default 10; used in matched operation.
- `include_resource_aware`, default false.

The dashboard selects the 10-day warm-up; the API allows the other declared sensitivity periods. Startup mode reports no warm-up. Reports include measured step bounds, input/initial-state digests and an optional candidate report.

Comparisons start from the preset or common preconditioned state, not the live evolved state. They do not inherit arbitrary live command toggles. Read the [evidence guide](evidence-guide.md) before publishing their output.

## Conflicts and bounded history

- **409 `STEP_CONFLICT`:** generation or expected step no longer matches. Refresh `/state`; do not blindly retry a stale mutation.
- **409 `IDEMPOTENCY_CONFLICT`:** the request ID was already used with different arguments. Resolve the caller's request bookkeeping.
- **422:** the payload does not satisfy the schema. Check field names, modes and bounds.

The conflict response includes a message, current step and run generation. Within a tab, the store queues dependent requests one at a time. Across tabs, the server detects competing updates and the dashboard pauses/refetches.

Event IDs increase across resets for the lifetime of a server. Retention is 1,000 records; advance replies contain at most the latest 200 new events, while the dashboard feed is also bounded. Truncation is explicit. Restarting the backend loses both the run and its history.

## Changing the contract or physics

For a contract change, update Python and TypeScript together, regenerate the step-0 fixture if needed, and test old/malformed snapshot rejection as well as normal rendering. Restart the backend after an upgrade; a frontend rebuild cannot update an already-running Python process.

For a physical change, put assumptions in `config.py`, retain all balance assertions, and run backend tests. Review how it affects scenarios, evidence and the shared editorial reference. A frontend fallback is not permission to replace a missing physical value with a plausible constant.

## Deployment settings and boundaries

`SIMULATION_BACKEND_URL` configures the rewrite destination. Set it before a production build when the backend is not local to the Next.js server. `NEXT_BUILD_DIRECTORY` and `NEXT_TYPESCRIPT_CONFIG` support the isolated browser-test build; normal development usually leaves them unset.

`SITE_URL` controls public metadata, not the API destination. It cannot repair an offline backend.

The single-worker restriction avoids separate process-local runs that would disagree. It does not make this an authenticated, persistent or production-ready control service. Before public mutation access, design security, access control, run ownership, persistence and operating limits explicitly. Real hardware integration is separate work, not an existing route in this API.
