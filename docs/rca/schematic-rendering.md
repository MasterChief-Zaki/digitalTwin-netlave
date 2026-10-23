# Connected schematic rendering

The site view is a compressed isometric schematic, not a surveyed site plan.
All physical elevation values use one display scale (0.16 scene units per meter).
Tree placement, equipment dimensions, and animation speed are decorative, not
additional simulation outputs. Canopy tint represents the engine's moisture
stress proxy; tree growth, survival and health are not modeled.

## Snapshot connections

- Reservoir water surface uses `surface_elevation_m` directly. Schema 1.2 exports
  `floor_elevation_m` and `depth_at_capacity_m` from Python configuration, so the
  basin and rim do not use inferred or contradictory frontend constants.
- Water-direction markers use only measured inlet, zone delivery and overflow
  flows. Requests or hydro watts never stand in for delivered water.
- Thin energy paths form a schematic DC bus. Solar/hydro generation, charging,
  discharging and admitted pump load use their corresponding snapshot powers.
  The animation does not imply every generated watt reaches the battery/pump.
- Battery fill uses snapshot SoC. Pump state uses `pump.running`; color follows
  the pumped-zone decision. Filter labels expose pressure drop/backflush state.
- Terrace status includes accepted scheduler deferrals as **Waiting**, along
  with safety waits; hard safety denials are **Fault**, delivered irrigation is
  **Active**, and no demand is **Idle**.
- Clicking a terrace or an accessible scene-zone button selects the dashboard's
  same Zustand zone ID. Selection and snapshot readings work without WebGL.
- Resets snap reservoir/battery visuals to the new run; frame updates only ease
  visual transitions. All physical state, time, accounting and decisions remain
  in Python. No allocation or physics in frame loops.

## Rendering and checks

Orthographic camera fitting is responsive, DPR is capped at 1.5, tree meshes are
instanced, colors come from night-palette tokens and three.js remains lazy loaded.
Procedural labels require no fonts/assets fetched by three.js. Water and energy
routes use shared equipment ports; arrows indicate symbolic direction rather
than hydraulic velocity. Overflow is explicitly an unmodeled receiving outlet.

The canvas exposes throttled diagnostic attributes for actual rendered water/
battery transforms, directional-marker visibility, zone status and projected
terrace coordinates. `tests/browser/twin.spec.ts` compares those to real Python
responses and clicks an actual terrace using its projected coordinates. It tests
manifold waiting, scheduler waiting, pump-reserve denial, cut inflow and shared
selection. `twin-fallback.spec.ts` verifies non-WebGL operation. These run with
all existing browser tests against isolated production Next.js/FastAPI servers.
