# Development troubleshooting

## Next.js

`next.config.ts` explicitly roots Turbopack in this repository using a portable file URL, independent of unrelated parent lockfiles. Keep the backend rewrite and isolated browser-build settings intact.

## Renderer compatibility

Fiber 9.8.2 still constructs `THREE.Clock`, deprecated by the installed three.js. A tracked pnpm patch replaces that construction with a Timer-backed bridge in its ESM/development-CJS/production-CJS bundles, preserving start, stop, elapsed time and manual advance. Frozen installs apply the patch; remove it when a compatible upstream release migrates the clock. Do not silence warnings or edit installed packages by hand.

Run `pnpm exec node scripts/check-fiber-timer.mjs` for bridge checks. `TwinCanvas` requests only WebGL2 (required by this three.js version) and selects `shadows="percentage"` instead of Fiber's default removed PCF soft-shadow constant. The dashboard remains usable without WebGL2. Python simulation state and accounting are unchanged.

## Browser diagnostics

If hydration mismatch details show only extra `fdprocessedid` attributes, a browser extension modified the DOM before hydration. Disable it for localhost or use a clean profile; do not suppress hydration errors or remove SSR. The Next.js dev-cache bypass notice on a hard refresh is informational. GPU shader/ReadPixels warnings are driver diagnostics, not application errors.

Next.js ESLint plugins currently declare peer ranges through ESLint 9. This project retains supported ESLint 10 and passes lint; downgrading to unsupported ESLint 9 merely to hide installation warnings is not a fix.

## Checks

Run `pnpm test:browser` for real-backend rendering, selection and fault checks. With the landing, product and twin dev servers on 3000/3001/3002 and the API on 8000, run `pnpm exec node scripts/check-dev-sites.mjs` for clean-profile dev console, mobile layout, product controls and no-WebGL fallbacks.
