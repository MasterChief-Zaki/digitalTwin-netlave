# P1 design study and deployment boundary

The [computed design study](design-study.json) runs six explicit hardware
configurations, two scenarios and both unchanged policies over 30 days at seed 7.
It is a single-seed synthetic sizing diagnostic, not a procurement recommendation.
The executing clean commit and full candidate configurations are recorded.

## Results

- Fixed-flow zone-C derating from 24 to 18 m³/h reduces worst-case pump demand at
  dead storage/flush-threshold clog from 3,236 W to 2,422 W, providing about 19%
  electrical margin. It does not meet the sustained low-solar service target:
  zone-C deficit remains about 31.5–32.9 mm over 30 days.
- Raising solar from 8 to 12 kWp reduces low-solar deficit to about 11.7–15.8 mm,
  but still does not establish a 5%-of-potential-ET service floor.
- Doubling battery capacity is not a solution to a persistent generation deficit;
  zone-C deficit remains about 32.5–33.8 mm.
- A 0.25 m zone-B mainline increases full-reservoir, flush-threshold-clog head
  margin from 0.59 to 1.76 m. It still misses the proposed 3 m design target.
- Halving filter loading reduces the synthetic loading burden but retains the
  exclusive shared-filter backflush. Zero flush-induced interruption cannot be
  promised without a different filtration arrangement.

No default hardware configuration was replaced and no variable-flow pump curve
was invented. Pressure-dependent application efficiency is not modeled. All
policy comparisons within a hardware candidate share configuration and inputs.

## Startup and warm-up sensitivities

[Startup diagnostics](startup-diagnostics.json) cover seeds 3/7/11 and five days.
The combined scheduler protects reservoir inventory, but the largest per-zone
additional deficits exceed 0.10 mm in baseline, clogged filter, low solar and
TSE interruption. These are diagnostic seeds, not held-out release evidence.
A validated refill-completion KPI is still needed before claiming the five-day
startup-refill target has passed; no such claim is made here.

[Warm-up sensitivity](warmup-sensitivity.json) covers 5/20-day common
preconditioning at seeds 3/7/11 with 30 measured days. Zone-C paired deficit
changes remain initialization-dependent, particularly under low solar. This is
sensitivity evidence only; it does not establish convergence or statistical
power. Independent-policy equilibrium initialization is not claimed.

## P2 deployment prerequisites — not implemented physical models

Before any real deployment:

1. Survey heads, reservoir geometry, pipes and filter hydraulics; measure pump
   curves and irradiance/battery performance with documented uncertainty.
2. Obtain effluent quality/solids and soil/species measurements, then recalibrate
   and rerun paired validation. No measurements are fabricated by this project.
3. Agree the agronomic service floor and surplus-TSE disposition with site
   engineers and the competent authorities. Persistent oversupply requires an
   approved outlet/inflow plan, not bigger buffering or intentional overwatering.
4. Decide whether salinity transport, pathogen exposure, tree health/growth and
   receiving-environment models are required for the intended decision. They are
   not simulated here; no carbon, survival or compliance claim is permitted.

**Release decision:** retain `SMART_HYSTERESIS` as default. Experimental scheduling
and synthetic studies are delivered; field calibration, hardware selection,
permits and default-policy promotion are not complete.
