# Shared brand and project facts

This guide is the same in all three NetLave repos. It explains what should stay consistent, where the facts come from, and how to publish them without overstating what the prototype proves.

## Three sites, one project

| Repository                                                                     | Its job                                              |
| ------------------------------------------------------------------------------ | ---------------------------------------------------- |
| [landing-netlave](https://github.com/MasterChief-Zaki/landing-netlave)         | Introduce the idea and founders.                     |
| [netlave](https://github.com/MasterChief-Zaki/netlave)                         | Explain the systems, scenarios and evidence.         |
| [digitalTwin-netlave](https://github.com/MasterChief-Zaki/digitalTwin-netlave) | Run the Python simulation and display its snapshots. |

Their home pages do not need identical layouts or every identical sentence. They do need the same project identity, assumptions, evidence boundaries and sources.

Every site publishes `src/content/ground-truth.json` and a server-rendered `/ground-truth` page. This is a common editorial reference: it lets a visitor find the same answer from any site. It is **not** another simulation model.

## What owns the facts?

There are three different kinds of information:

1. **Physical assumptions:** the twin's `backend/config.py` owns the parameters. `backend/scenarios/presets.py` owns the starting conditions and fault presets.
2. **Simulation evidence:** a trial or report records its inputs, source revision and results. Its original provenance must remain attached to it.
3. **Website copy:** `ground-truth.json` gives a pinned, readable summary of those assumptions and reports. Live twin readings still come from Python snapshots, not this JSON.

A new website commit does not make an old trial a new trial. For example, the published baseline uses seed 7 and 14 simulated days including startup. The later resource-aware validation uses common warm-up and held-out trials. They answer different questions and must not be presented as interchangeable results.

## How to talk about NetLave

Use **NetLave** for the name and **simulation-driven prototype** for its current status. In ordinary sentences, explain what a number represents instead of attaching a large warning to every paragraph.

| Clear wording                                     | Avoid                                     |
| ------------------------------------------------- | ----------------------------------------- |
| “The model assumes an 8 kWp solar array.”         | “The installation has 8 kWp of solar.”    |
| “The pump stops at the modelled battery reserve.” | “The forest is proven self-powered.”      |
| “This synthetic baseline did not save water.”     | “Smart control guarantees water savings.” |
| “Tree color shows a moisture-stress proxy.”       | “The twin measures tree health.”          |

Smart hysteresis remains the default. Resource-aware scheduling is implemented but experimental and opt-in because held-out validation did not establish acceptable irrigation service at every endpoint.

Synthetic quality flags never authorize real-world irrigation. Site surveys, treatment-grade and water-quality checks, species approval, worker protection and current reuse permissions remain real deployment requirements. Salinity, pathogens, tree growth and carbon sequestration are not modelled.

The landing page identifies Eyad, Mahmoud, Omar and Hana and publishes their existing portraits. Detailed role biographies have not been supplied, and no contact email has been verified. The landing page's contact button opens the project repository homepage so visitors can learn more and follow development; it does not point directly to the issues page.

## Update a shared fact without creating drift

Use this order:

1. **Check the source.** Read the Python configuration, preset or published validation that supports the change. Do not change physics to match marketing copy.
2. **Decide what changed.** A clearer sentence may keep the same source revision. A new assumption or result needs the actual supporting revision or report, not merely the latest site commit.
3. **Update the shared JSON.** Keep the units, synthetic status, source links and claim limits together.
4. **Copy the shared change to all three repos.** If you changed the reference-page wording, copy its TSX and SCSS too. Review product-only text that may repeat the old claim.
5. **Run the comparison.** From any repo, with all three adjacent:

   ```bash
   pnpm exec node scripts/check-shared-truth.mjs --siblings
   ```

6. **Check Python consistency in the twin.** `pnpm test:backend` includes `test_site_ground_truth.py`, which compares published parameters, zone properties and scenario IDs with Python.
7. **Run each repo's regular checks and submit its PR.** Keep the shared update understandable in the PR description.

Without adjacent repos, omit `--siblings`. That checks the local reference and favicon structure only; it does not prove the other sites agree.

The sibling check compares the JSON, fonts, artwork, icons, reference page and `llms.txt`. It normalizes text line endings and compares binary assets exactly. It does not validate the science behind a sentence, compare every home-page paragraph or refresh historical reports. Source review is still needed.

## Logo files and when to use them

`public/brand/source.png` is the supplied `NetLave.png`, kept unchanged. The generated files are derived from that artwork, not a redrawn approximation.

| Asset                    | Purpose                                                                         |
| ------------------------ | ------------------------------------------------------------------------------- |
| `mark.png`               | Dark monogram on a pale padded background; used in headers and to create icons. |
| `logo-light.png`         | Light full logo for dark surfaces; the flat purple background is removed.       |
| `social.png`             | 1200 × 630 social-sharing image.                                                |
| `src/app/favicon.ico`    | Browser favicon with 16, 32 and 48px entries.                                   |
| `src/app/icon.png`       | 192px application icon.                                                         |
| `src/app/apple-icon.png` | 180px touch icon.                                                               |

Regenerate them with:

```bash
pnpm exec node scripts/generate-brand.mjs
```

The script uses Sharp already installed with Next.js. It crops the monogram from the upper panel at `(535, 141, 475, 524)` and the light lockup from the lower panel at `(535, 1131, 475, 691)` of the 1545 × 1999 source. If the source artwork changes, review these crop coordinates before generating anything.

The favicon PNG payloads must remain RGBA, which the generator ensures. Next.js's App Router discovers the icon files automatically; do not restore starter icons or add conflicting hand-written icon tags.

After regeneration, inspect the small favicon as well as the full logo, copy the resulting assets to all three repos, and run the sibling check.

## Fonts and controls

`src/styles/fonts.ts` is identical across repos:

- **Space Grotesk:** variable font for headings and body text.
- **IBM Plex Mono:** weights 400, 500 and 600 for labels, code and readings.
- Latin subset and `swap` display behavior for both.

Next.js obtains the Google font files during a build and serves them from the site afterward. Do not describe a first install or uncached build as guaranteed offline. The logo's lettering is part of the image; it is not the body font.

The landing and product sites share the same glass-control design, although their SCSS is organized differently. Keep the rounded capsules, tinted primary/clear secondary contrast, visible selected states and reduced-motion/transparency behavior. The twin's denser operational controls keep their own layout while using the same typography and palette.

## Publishing: search and generative discovery

SEO helps search engines understand the pages. GEO here means helping generative answer systems find clear, attributable project information. Neither is a reason to add unsupported claims or promise a ranking.

The existing setup includes:

- Unique descriptive home-page titles and a shared project description.
- Open Graph and Twitter social-card metadata.
- Sanitized `WebSite` JSON-LD describing the prototype without fake ratings or offers.
- A linked, server-rendered `/ground-truth` page with direct answers, units, evidence and pinned sources.
- `robots.txt`, `sitemap.xml` and an `llms.txt` discovery aid.

`llms.txt` is guidance for discovery, not a guarantee that a crawler will read it or an answer engine will cite the project. The useful part is still the visible, well-sourced reference page.

### Set the real production origin before building

Each deployment needs its own `SITE_URL`, such as an actual verified HTTPS origin. It must not include a path, query or fragment. No production domains are supplied by these repos, so the code does not guess them.

Set the environment variable in the hosting platform before the build. Locally, you can put it in an untracked `.env.local`. Use the site's real origin when preparing a public build—not `localhost`, a made-up domain or a temporary preview address.

| Setting               | What the site emits                                                                               |
| --------------------- | ------------------------------------------------------------------------------------------------- |
| `SITE_URL` configured | Self-canonical URLs, absolute social-image URLs and a sitemap containing `/` and `/ground-truth`. |
| `SITE_URL` absent     | No explicit production canonical or absolute social-image URL; empty sitemap.                     |
| `VERCEL_ENV=preview`  | `noindex`/`nofollow`, crawl blocking and no sitemap entries.                                      |

`robots.txt` allows public content but excludes `/api/`. That is a crawler hint, **not access control**. The twin backend has no authentication; do not expose its command endpoints as a production control service without a separate security design.

On a non-Vercel preview host, configure equivalent noindex/crawl protection yourself. The code does not automatically recognize every host's preview environment.

### Review a deployment

1. Open `/` and `/ground-truth` and inspect their titles, descriptions, canonical links and social-image URLs.
2. Open `/robots.txt` and `/sitemap.xml`; make sure they contain the intended production origin and no temporary domain.
3. Open the social image and favicon. Check that their URLs are public and return the correct assets.
4. Validate JSON-LD with the [Schema.org validator](https://validator.schema.org/). It should describe what visitors can actually read.
5. Check mobile, keyboard navigation and no-WebGL rendering. Clear source material should not depend on the decorative scene.
6. Submit the real sitemap to the appropriate search consoles if you manage that deployment.

Keep each home page self-canonical; the founder page and interactive twin are not duplicates of the product page. The shared reference is intentionally repeated. Choose a cross-domain canonical for that reference only after deciding which public domain should own it.

For page-specific changes, use the README's site guide or the twin's dashboard guide. For a technical warning, use [development troubleshooting](development-troubleshooting.md).
