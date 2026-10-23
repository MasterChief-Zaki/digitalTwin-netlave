# NetLave Digital Twin

This repository runs NetLave's simulation-driven prototype of treated-wastewater forestry irrigation in Egypt. It models reclaimed water entering a reservoir, three drip-irrigation zones, a shared filter, renewable generation and the limits on an uphill pump.

The purpose is to make decisions explainable: **a zone can ask for water without being able to receive it**. The controller proposes irrigation; the safety resolver checks whether the model can safely deliver it. The dashboard shows the resulting state and the reason for each decision.

One deterministic Python engine owns physical state and time. The Next.js dashboard, charts and 3D schematic display its snapshots; they do not run their own physics.

> This is a software prototype using synthetic site assumptions. It is not synchronized with or calibrated against a real installation. Its outputs are simulated, not measured savings, proof of electrical autonomy or regulatory approval. Synthetic quality flags never authorize real-world irrigation.

## Start here

You do not need to read every technical report to use the dashboard.

| If you want to…                                     | Read…                                                            |
| --------------------------------------------------- | ---------------------------------------------------------------- |
| Run a first demo                                    | The setup below, then [dashboard guide](docs/dashboard-guide.md) |
| Understand the site assumptions and physical limits | [Model reference](docs/model-reference.md)                       |
| Work on the engine, snapshot contract or API        | [Architecture and API](docs/architecture-and-api.md)             |
| Interpret controller comparisons                    | [Evidence guide](docs/evidence-guide.md)                         |
| Update shared copy, branding or search metadata     | [Brand and ground truth](docs/brand-and-ground-truth.md)         |
| Fix a connection or rendering problem               | [Troubleshooting](docs/development-troubleshooting.md)           |
| Contribute a change                                 | [Repository rules](AGENTS.md)                                    |

## Run locally

Use Node.js 24, pnpm 10 and [uv](https://docs.astral.sh/uv/). uv installs the pinned Python 3.14 runtime when needed. Use **pnpm for JavaScript and uv for Python**; do not introduce npm/yarn lockfiles, pip environments or `requirements.txt`.

From this repository:

```bash
pnpm install --frozen-lockfile
pnpm backend:setup
pnpm demo
```

`pnpm demo` builds the dashboard and starts both servers:

- Dashboard: http://localhost:3000
- Simulation API: http://127.0.0.1:8000

Wait for the dashboard to show **Live backend** before using playback. Here, “live” means connected to the simulation server, not a physical installation. Before it connects, the page displays a labelled step-0 fixture.

The initial install and an uncached build need network access for dependencies, Python and font files. After building, the browser uses self-hosted fonts and local simulation data. Do not assume a new machine can build everything offline.

Ctrl+C in the demo terminal stops both servers. Ports 3000 and 8000 must be free before starting it.

### Development: use two terminals

For hot-reloading frontend work, run:

```bash
# Terminal 1, in digitalTwin-netlave
pnpm backend:dev

# Terminal 2, in digitalTwin-netlave
pnpm dev
```

The browser sends `/api/*` requests to Next.js, which proxies them to FastAPI on port 8000. Python does not tick in the background; only an advance request moves simulated time.

The backend command does not enable automatic Python reload. After changing backend code or upgrading the snapshot schema, restart the backend yourself.

### Run all three sites together

Each Next.js app defaults to 3000. In separate terminals, run these commands inside the named repo:

| Repository            | Command                | URL                   |
| --------------------- | ---------------------- | --------------------- |
| `landing-netlave`     | `pnpm dev --port 3000` | http://localhost:3000 |
| `netlave`             | `pnpm dev --port 3001` | http://localhost:3001 |
| `digitalTwin-netlave` | `pnpm dev --port 3002` | http://localhost:3002 |

Keep `pnpm backend:dev` running in a fourth terminal on 8000. Only the twin needs it. Do not run `pnpm demo` alongside this layout unless its default ports are free.

## A first five-minute walkthrough

1. Load **Baseline**, seed **7**, with **Smart hysteresis**. Changing the selectors alone does not apply them; press **Load run**.
2. Press **+1 min**. A and C begin irrigating; B waits because A and B share a limited gravity manifold.
3. Select B and read its requested flow, delivered flow and reason. The distinction is the point of the demo.
4. Load **Low solar (sandstorm)**. Step through the first minutes and watch C's pump stop at the 20% battery reserve. A manual Open cannot override that limit.
5. Try **Clogged filter**, then read the water and energy cost of its exclusive flush.
6. Run a short A/B experiment. Check ET service and final stocks alongside water delivery and pump energy; lower delivery alone is not a success.

The [dashboard guide](docs/dashboard-guide.md) explains each panel, playback and the experiment options in more detail.

## The model at a glance

These are assumptions, not surveyed site values:

| Part             | Default model                                                   |
| ---------------- | --------------------------------------------------------------- |
| Forest           | 15 ha: A 6 ha and B 5 ha by gravity; C 4 ha pumped uphill       |
| Reservoir        | 1,500 m³ capacity; 900 m³ initially; 50 m³ dead volume          |
| Mean TSE inflow  | 60 m³/h, with a synthetic daily pattern                         |
| Energy           | 8 kWp solar; 15 kWh battery; 3 kW pump electrical limit         |
| Micro-hydro      | About 294 W at mean inflow and the assumed 3 m recoverable drop |
| Moisture control | Start below 0.166 m³/m³; stop at 0.198 m³/m³                    |
| Time             | Deterministic 60-second simulation steps                        |

The full table, sources and balance checks are in the [model reference](docs/model-reference.md). `backend/config.py` remains authoritative; `GET /scenarios` serves its assumption register.

Every step checks reservoir, soil, electrical-bus and battery-cell balances. A failed balance raises an error; it is not weakened or replaced with a hard-coded outcome.

## Controllers and evidence

**Smart hysteresis stays the default.** Fixed timer is available for comparison. Manual open/close is a per-zone mode, not a separate selectable policy; it still passes the safety gates.

Resource-aware scheduling is implemented but **experimental and opt-in**. It schedules bounded automatic sessions using current water, head and energy budgets. It is not allowed to know future realized weather or bypass safety. Published held-out trials did not establish acceptable service at every endpoint, so there is no automatic promotion to default.

The historical synthetic baseline (seed 7, 14 days) is reported honestly:

| Metric                            | Fixed timer | Smart hysteresis |
| --------------------------------- | ----------: | ---------------: |
| Irrigation delivered              |   11,404 m³ |        11,411 m³ |
| ET deficit                        |     0.42 mm |          0.56 mm |
| Overflow / diversion              |    8,245 m³ |         8,139 m³ |
| Pump energy                       |     360 kWh |          399 kWh |
| Unserved admitted electrical load |       0 kWh |            0 kWh |

Smart hysteresis did **not** save water in this baseline. The timer was already sized from ET, and the shared network makes requests queue. These rounded historical outputs are not new field measurements or the later warm-up/held-out scheduler trial. See the [evidence guide](docs/evidence-guide.md) before interpreting or publishing a comparison.

## Find your way around the code

```text
backend/config.py          Synthetic parameters and assumption register
backend/main.py            FastAPI routes, mutation lock and event/retry ledgers
backend/schemas.py         Schema 1.2 contract
backend/twin/              State, inputs, stepping and snapshot projection
backend/models/            Soil/water, hydraulics, energy and filtration
backend/control/           Requests, experimental scheduler and safety gates
backend/scenarios/         Presets, comparisons and evaluation runners
backend/tests/             Contract, conservation, scenarios and report checks
src/components/dashboard/  Readings, zones, faults, charts, ledger and experiments
src/components/twin/       Snapshot-driven schematic and selection
src/store/useTwinStore.ts  Latest snapshot, UI state and single-flight playback
src/services/api.ts        Typed API client and snapshot compatibility checks
src/types/simulation.ts    TypeScript mirror of the Python contract
src/content/               Shared editorial facts, not live physics
src/fixtures/              Step-0 snapshot used before connection
```

For the complete request-to-snapshot path and endpoint details, use [architecture and API](docs/architecture-and-api.md).

## Check a change

```bash
pnpm lint
pnpm lint:styles
pnpm format:check
pnpm typecheck
pnpm test:backend
pnpm exec node scripts/check-fiber-timer.mjs
pnpm build
pnpm exec playwright install chromium
pnpm test:browser
```

Browser tests build a separate production dashboard and start a private backend on ports **3100/8100**, using `.next-browser/` and `tsconfig.browser.json`. They do not reuse or reset your demo. Keep those ports free. They check rendered transforms and selection against real Python replies, not just text labels.

For shared-file consistency, run `pnpm exec node scripts/check-shared-truth.mjs --siblings` with the three repos adjacent. For the three running dev sites on 3000/3001/3002 and API 8000, run `pnpm exec node scripts/check-dev-sites.mjs` from here.

CI runs backend, Timer, lint/style/type/build and browser checks. Existing unit and browser tests establish software behavior, not hardware readiness or forest health. Avoid running a heavy evaluation sweep beside the timing benchmark; machine load can affect its result.

Follow [AGENTS.md](AGENTS.md): keep commits atomic, use plain-English summaries, retain pre-commit hooks and send changes through PRs to `main`. Larger work uses epic branches and `--no-ff` part merges. Python and TypeScript schema changes must move together.

## Deployment is not just a frontend build

`pnpm build` and `pnpm start` serve the production dashboard, but the API must also be running and reachable through the Next.js rewrite. Set `SIMULATION_BACKEND_URL` at build time if it is not `http://127.0.0.1:8000`.

Set `SITE_URL` to this dashboard's verified production origin before building if you need canonicals, absolute social-card URLs and a populated sitemap. The shared [publishing guide](docs/brand-and-ground-truth.md#publishing-search-and-generative-discovery) explains previews and crawler behavior.

The backend has **one shared in-memory run, no persistence and no authentication**. Restarting it loses the run and event history. Multiple tabs can affect the same run. Do not expose its mutation endpoints as a production control system without a separate security, persistence and operating design. `robots.txt` is not access control.

A real TSE deployment also needs surveyed hydraulics, measured water/soil/species data, calibration, validation and current reuse approvals. Salinity, pathogens, tree growth and carbon are not modelled. The [design and deployment boundary](docs/rca/validation/design-and-deployment.md) lists what remains open.

## Detailed and historical material

- [Experimental scheduler](docs/rca/scheduler.md): operating budgets and deferrals.
- [Schematic rendering](docs/rca/schematic-rendering.md): which snapshot fields drive the scene.
- [Paired protocol](docs/rca/paired-protocol.md): the declared held-out evaluation method.
- [RCA evaluation specification](docs/rca/evaluation-spec.md): original reference and accounting rules. RCA means root-cause analysis here.
- [Original execution plan](docs/superpowers/plans/2026-10-23-digital-twin.md): historical decisions, not a replacement for current code.

Read the guides first; open the formal protocols when you need to inspect or reproduce their exact rules.
