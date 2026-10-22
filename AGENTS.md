<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# netLave Digital Twin

A simulation-driven digital twin of a self-powered, treated-wastewater (TSE) irrigated forest in Egypt. One deterministic Python simulation owns every physical value; the Next.js dashboard and the 3D forest only display the snapshots it returns. Keep it simple: build only what is asked, the way it is asked. No speculative abstractions, features or dependencies.

## Stack

- Frontend: Next.js 16 (App Router, `src/app/`), React 19, TypeScript (strict)
- Styling: SCSS modules (`*.module.scss`), globals in `src/app/globals.scss`, design tokens in `src/styles/_tokens.scss` (the NetLave night palette)
- 3D: three.js through React Three Fiber (`@react-three/fiber`) with drei (`@react-three/drei`) helpers
- Charts: Recharts. Client state: Zustand.
- Backend: Python 3.12+ (pinned to 3.14 in `backend/.python-version`), FastAPI and Pydantic in `backend/`, tested with pytest
- Import alias: `@/*` → `src/*`

## Commands

Use **pnpm** only for JavaScript. Never npm or yarn, and never commit another lockfile.

Use **uv** only for Python: dependencies live in `backend/pyproject.toml` and `backend/uv.lock`. Add them with `uv add` (or `uv add --dev`) from `backend/`, and run Python through `uv run`. Never pip, a hand-made venv or a `requirements.txt`.

| Command               | Purpose                                         |
| --------------------- | ----------------------------------------------- |
| `pnpm dev`            | Start the Next.js dev server                    |
| `pnpm demo`           | Build, then serve the dashboard and the backend |
| `pnpm build`          | Production build                                |
| `pnpm lint`           | ESLint (`next lint` is removed)                 |
| `pnpm lint:styles`    | Stylelint for CSS/SCSS                          |
| `pnpm format`         | Prettier, write changes                         |
| `pnpm format:check`   | Prettier, check only                            |
| `pnpm typecheck`      | Generate Next types, run `tsc`                  |
| `pnpm backend:setup`  | `uv sync`: install the locked backend environment |
| `pnpm backend:dev`    | Start the FastAPI server on port 8000           |
| `pnpm test:backend`   | Run the backend test suite                      |

A Husky pre-commit hook runs lint-staged (ESLint, Stylelint, Prettier on staged files) and then `pnpm typecheck`. Never bypass it with `--no-verify`. Fix the problem instead. Run `pnpm test:backend` before committing backend changes.

## Simulation rules

- Python owns all physical state, time, controller decisions, accounting and event IDs. The frontend never computes physics; it renders the latest snapshot.
- The JSON contract is snake_case with units in every dimensional key. `backend/schemas.py` and `src/types/simulation.ts` change together.
- Every simulated number comes from the engine and documented assumptions in `backend/config.py`. Never hard-code outcomes or KPIs.
- Mass and energy balances are asserted every step. Never weaken a balance check to make a test pass.

## Code style

- Clean, readable design. Give components, classes, CSS classes, variables and functions clear, descriptive names. No vague names like `data`, `tmp` or `x`.
- TypeScript is stricter than `strict`: `noUncheckedIndexedAccess`, `noImplicitOverride`, `noImplicitReturns` and `noFallthroughCasesInSwitch` are on, and ESLint uses typescript-eslint's strict type-checked rules. Handle the `undefined` cases instead of silencing them with `!` or `as`.
- Don't allocate inside `useFrame`: no `new` and no `.clone()` in the frame loop. Create objects once, outside the loop. Never run physics in `useFrame`; it only interpolates visuals.
- Python: standard-library dataclasses and scalar math, type hints everywhere, PEP 8 names.
- Let Prettier and the linters decide formatting. Don't hand-tune it.

## Git workflow

- `main` is protected: every change goes through a PR targeting `main`.
- Branch names: `<type>/<short-description>`, e.g. `ci-cd/precommit-and-linting`, `docs/add-agent-md`.
- Larger work goes on an `epic/<short-description>` branch: build each part on its own branch, merge it into the epic with `--no-ff`, and open one PR from the epic to `main`.
- Keep commits atomic and scoped: one logical change per commit.
- Write commit messages like a human: short, plain-English summaries of what changed.
- No AI attribution anywhere: no `Co-Authored-By` trailers or "Generated with" lines in commits, PRs or code.
