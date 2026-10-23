# Shared NetLave brand and ground truth

## Authority and site roles

All three repos publish the same `src/content/ground-truth.json` and the same server-rendered `/ground-truth` reference. Home-page layouts remain distinct: the landing page introduces the founders, the product site explains systems and scenarios, and the twin dashboard operates the simulation.

The Python engine in [digitalTwin-netlave](https://github.com/MasterChief-Zaki/digitalTwin-netlave) is the only physical authority. `backend/config.py` owns parameters; `backend/scenarios/presets.py` owns presets. The JSON is a static, pinned editorial reference, not a second engine or a substitute for live snapshots. Provenance links pin the reference commit. The historical seed-7, 14-day comparison is distinct from later warm-up/held-out scheduler trials.

Always call the project **NetLave**. Say **simulation-driven prototype**, **synthetic assumptions** and **simulated outputs**. Do not claim proven self-power, field savings, tree health, carbon sequestration or regulatory compliance. Smart hysteresis remains the default; resource-aware control is experimental and opt-in.

The founder names and existing portraits come from the landing repository. Roles/bios were not supplied, so placeholders are not published. No email is verified; the existing public GitHub issue tracker is linked instead. Do not post private information there.

## Logo and typography

- `public/brand/source.png` is the unmodified user-supplied `NetLave.png` (1545 × 1999).
- `scripts/generate-brand.mjs` crops the supplied dark monogram (535, 141, 475, 524), pads it on the artwork's pale background, and exports `mark.png`, PNG icons and a 16/32/48-pixel ICO.
- The lower light lockup is cropped at (535, 1131, 475, 691). Only the flat purple background is removed; no logo geometry is redrawn. `logo-light.png` is for dark surfaces. `social.png` is a 1200 × 630 card made from this lockup.
- Regenerate with `pnpm exec node scripts/generate-brand.mjs`. It uses Sharp already installed with Next.js; no added dependency.
- `src/styles/fonts.ts` is identical across repos: Space Grotesk variable for headings/body, IBM Plex Mono 400/500/600 for labels, code and metrics, Latin subset and swap display. Next.js self-hosts the fonts after build. The artwork's embedded lettering is preserved, not used as a body font.
- Next.js App Router serves `src/app/favicon.ico`, `icon.png` and `apple-icon.png` automatically. Do not restore the starter icons.

## Synchronizing changes

1. Verify changes against Python configuration, presets and published validation. Never edit physics to fit marketing copy.
2. Update `ground-truth.json` with a real source commit and copy it to all three repos. Keep claim limits visible in the UI, not just metadata.
3. Keep the shared font file, reference page, discovery file and generated branding byte-identical.
4. From any repo run `pnpm exec node scripts/check-shared-truth.mjs --siblings` with all three repos next to each other. Without siblings, omit `--siblings` for local checks.
5. In the twin run `pnpm test:backend`: `test_site_ground_truth.py` compares the published parameters, zones and scenario IDs with Python.
6. Run the repository's lint, style, formatting, type and production-build checks. Follow `AGENTS.md`, use pnpm (uv for Python), retain pre-commit hooks and submit PRs to `main`.

## SEO and generative discovery

- Each home page has a unique descriptive title; descriptions and claim boundaries use the shared reference. Open Graph/Twitter cards and sanitized WebSite JSON-LD describe the prototype without fake ratings, offers, organizations or field results.
- `/ground-truth` provides crawlable semantic headings, direct answers, a parameter list, historical evidence table and pinned source citations, without JavaScript or WebGL. Every home page links to it.
- `public/llms.txt` is a discovery aid, not a standard ranking guarantee. It directs readers to the reference and physical authority and retains claim limits.
- Set **`SITE_URL=https://your-verified-production-origin` at build time**, separately in each deployment. This must be an HTTP(S) origin without a path/query/fragment. No real domains were supplied or recorded in these repos, so domains are not guessed. Without it, absolute canonicals and social image URLs are omitted and the sitemap is empty; set it before public release.
- `/robots.txt` allows public content but excludes `/api/`. `/sitemap.xml` includes `/` and `/ground-truth` only when a production origin is configured. `VERCEL_ENV=preview` emits noindex/nofollow and blocks crawling; protect previews on other hosts similarly.
- Each domain self-canonicalizes: do not canonicalize the interactive twin or founder page to the product site. The shared reference is intentionally identical; assign a cross-domain reference canonical only after deciding the authoritative public domain.
- After deployment, inspect canonical/OG tags, verify sitemap origins, validate JSON-LD with Schema.org's validator, submit the sitemap to search consoles, and test desktop/mobile rendering. Better discovery is not a promise of search or generative-answer placement.
