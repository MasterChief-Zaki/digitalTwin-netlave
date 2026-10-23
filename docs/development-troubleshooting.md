# Development troubleshooting

Start with the connection badge, the Next.js terminal and the Python terminal. The dashboard can display a labelled fixture or its last snapshot even when the backend is unavailable; a visible page does not necessarily mean the model is connected.

## Quick checks

| Symptom                               | First check                                                                  |
| ------------------------------------- | ---------------------------------------------------------------------------- |
| Playback is disabled                  | Does the badge say Live backend? Is FastAPI running?                         |
| The page works but `/api/state` fails | Check the Next.js rewrite destination and backend reachability.              |
| A snapshot is rejected                | Restart the backend after a schema upgrade; current contract is 1.2.         |
| Another tab pauses your run           | Expected conflict handling for the one shared server run.                    |
| The schematic is absent               | Check WebGL2 support; readings and selection should remain usable.           |
| A comparison takes time               | It runs private Python steps; wait for the response before assuming failure. |
| Browser tests cannot start            | Are the isolated ports 3100/8100 free? Is Chromium installed?                |

## Connect the frontend and backend

From this repository, use two terminals:

```bash
# Terminal 1
pnpm backend:dev

# Terminal 2
pnpm dev
```

The backend is on `http://127.0.0.1:8000`. Next.js is normally on 3000, or 3002 in the three-site dev layout.

Check both paths:

1. Open `http://127.0.0.1:8000/state` to check FastAPI directly.
2. Open `/api/state` on the dashboard's actual origin to check the Next.js proxy.

If the first works and the second does not, inspect `next.config.ts` and `SIMULATION_BACKEND_URL`. If neither works, inspect the Python terminal first. The default backend command does not automatically reload Python changes; restart it after editing backend code or upgrading the schema.

Before connecting, the page uses the step-0 fixture. On connection failure, it pauses and retains displayed information rather than inventing new simulated values. The dashboard retries connection, but it cannot repair a stale Python process or an unreachable rewrite destination.

## Understand shared-run conflicts

One backend process owns one in-memory run. Multiple browser tabs can move that same run. A stale generation or expected step returns 409 `STEP_CONFLICT`; the dashboard pauses and refreshes.

That is protection against applying old mutations, not proof of isolated user sessions. Use a separate backend process/configuration if you need an independent local experiment. Restarting the backend loses the run and event history.

A reset creates a new generation. Events can remain visible across resets because their IDs continue for the server's lifetime. A comparison is different: it uses private states and does not reset the live run.

## Schema or geometry errors

The current snapshot schema is 1.2. Python and TypeScript contracts must agree, including reservoir floor/depth and service diagnostics. The API client rejects an old or malformed snapshot before the renderer uses it.

After an upgrade:

1. Restart FastAPI so it loads the new Python contract.
2. Restart/rebuild Next.js if dependencies or build settings changed.
3. Inspect `/state` and the request error, not just the canvas.
4. Run backend contract tests and the browser compatibility tests.

Do not make an old backend appear compatible by hard-coding missing geometry or removing validators.

## WebGL and the Timer patch

`TwinCanvas` checks WebGL2 because the installed three.js renderer requires it. A browser without it gets a clear fallback; zone selection and all model values remain in the dashboard.

Installed Fiber 9.8.2 still constructs `THREE.Clock`. The tracked pnpm patch uses a Timer-backed bridge in ESM and both CJS bundles, preserving start/stop, elapsed time and manual advance. Frozen installs apply it reproducibly:

```bash
pnpm install --frozen-lockfile
pnpm exec node scripts/check-fiber-timer.mjs
```

Restart Next.js after dependency installation. Do not edit installed packages or filter warnings. When a compatible upstream version migrates the clock, remove the patch deliberately and rerun the Timer/scene regression checks.

The canvas explicitly uses `shadows="percentage"`, the supported PCF path, instead of the removed soft-shadow constant. These compatibility choices affect drawing only. Python time, water balances and energy accounting remain unchanged.

For a mobile overflow problem, fix the offending grid/flex/table container. The experiment header wraps controls, and wide tables have their own scrolling areas. Hiding overflow on the entire dashboard can make important readings inaccessible.

## Tests and slow runs

`pnpm test:browser` builds a private production dashboard and starts FastAPI on **3100/8100**. It does not reuse the normal demo. Keep both ports free and install its browser with `pnpm exec playwright install chromium`.

For a browser-test failure, inspect the trace/error context in `test-results/` and the relevant Python response. CI uploads failure artifacts. A text label passing does not prove the actual reservoir or tree transform is correct; the scene tests check rendered state too.

The 14-day backend comparison has a five-second timing gate. Heavy evaluation sweeps or other system load can affect it. Rerun a timing failure alone before attributing it to physics changes. Keep the threshold intact; a reproducible performance regression still needs investigation.

Longer held-out evaluation sweeps are separate from the normal test suite. Small diagnostic runs do not satisfy their release rules. See the [evidence guide](evidence-guide.md#reproduce-deliberately).

## Browser-only messages

A hydration report containing only extra `fdprocessedid` attributes was traced to extension DOM injection in the observed browser. Disable that extension on localhost or use a clean profile. If other content differs, investigate it normally instead of assuming the same cause or suppressing hydration checks.

Next.js's `cache-bypass-in-dev` notice on a hard refresh is informational. GPU/ANGLE shader precision or ReadPixels messages can be driver diagnostics; verify actual rendering and fallback behavior. Do not switch off validation solely to hide them.

Some installed Next.js ESLint plugins declare peer ranges through ESLint 9 while this repo uses ESLint 10. Keep running lint and fix actual failures. Downgrading merely to remove a peer warning is not a compatibility solution.

## Build settings and public metadata

`next.config.ts` explicitly roots Turbopack in this repo. Keep the portable file URL rather than relying on unrelated parent lockfiles or a hard-coded home directory. Read the installed Next.js guides before changing configuration APIs.

- `SIMULATION_BACKEND_URL` chooses the rewrite destination; set it before building when FastAPI is elsewhere.
- `NEXT_BUILD_DIRECTORY` and `NEXT_TYPESCRIPT_CONFIG` isolate browser-test output; leave them unset for normal builds unless deliberately using a separate configuration.
- `SITE_URL` sets the public origin for metadata; it does **not** configure the API connection.

Without `SITE_URL`, an empty sitemap is intentional. Rebuild with the verified production origin before checking canonicals and social-card URLs. Read [publishing guidance](brand-and-ground-truth.md#publishing-search-and-generative-discovery) for preview indexing and access-control boundaries.

## Confirm the fix

Run the checks in the [README](../README.md#check-a-change). With landing/product/twin dev servers on 3000/3001/3002 and API on 8000, also run:

```bash
pnpm exec node scripts/check-dev-sites.mjs
```

This checks clean-profile dev-console errors, product controls, mobile layout and no-WebGL fallbacks across the three sites. It does not establish field calibration, hardware safety or authenticated production operation.
