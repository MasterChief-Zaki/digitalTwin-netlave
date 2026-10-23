# Model reference

The model connects a water budget, a soil budget and an electrical budget. A controller can request irrigation, but delivery must fit all three. This guide explains the physical assumptions without asking you to read the engine first.

## Start with the units

- **TSE** means treated sewage effluent: reclaimed water assumed available for forestry irrigation, not drinking water.
- **ET** is evapotranspiration, the modelled water demand from soil evaporation and vegetation transpiration. **ET0** is its reference climate input; the crop coefficient scales it.
- **Head** is the pressure/elevation budget expressed in metres of water. The uphill pump must overcome static lift, emitter pressure and losses; elevation alone is not its total load.
- **SoC** is battery state of charge. **CI** is the synthetic filter clog index.
- Flow (m³/h) and power (W) describe a rate; volume (m³) and energy (kWh) describe accumulated quantities.

## How the model behaves

TSE enters through the inlet turbine and reaches the reservoir. Gravity supplies A and B through a shared manifold; C needs an uphill pump. All zones share a filter. Soil buckets gain infiltrated irrigation and lose actual ET and drainage. Solar, hydro and battery storage supply admitted electrical loads.

A request receives its rated flow or no flow. There is no measured pump curve, variable-flow controller or pressure-dependent application efficiency. ET0 and solar are synthetic inputs, not live weather forecasts. The filter represents solids loading, not pathogen removal or salinity control.

The controller requests water. The resolver checks quality, flush state, usable storage, hydraulic head, shared flow and available electrical energy before granting it. Manual requests pass the same safety gates. The experimental scheduler can defer automatic demand before these gates; it does not replace them.

## Where the parameters come from

`backend/config.py` owns the values and the `ASSUMPTIONS` register. `GET /scenarios` serves that register to clients. The source strings in the following table document modelling choices; they are not proof that those values were measured at a real site.

If a parameter changes, update this reference and the shared editorial JSON where applicable, then test the model. Do not hard-code a matching KPI in the frontend. The [shared guide](brand-and-ground-truth.md) explains the cross-repo steps.

## Synthetic site assumptions

These are assumptions for a synthetic Egyptian forestry site, not Serapium field measurements. A real deployment replaces them with surveyed head, a measured TSE hydrograph, pipe design, treatment grade, water-quality records, soil laboratory values and species-specific agronomy. The live table is served by `GET /scenarios` from `backend/config.py`.

| Parameter                                              | Value                            | Unit                    | Status  | Source                                               |
| ------------------------------------------------------ | -------------------------------- | ----------------------- | ------- | ---------------------------------------------------- |
| Zone areas A / B / C                                   | 6 / 5 / 4                        | ha                      | assumed | Execution plan V5.0, section 5 (synthetic)           |
| Zone feed A / B / C                                    | gravity / gravity / pumped       | -                       | assumed | Execution plan V5.0, section 5 (synthetic)           |
| Zone elevations A / B / C                              | +2 / +8 / +34                    | m                       | assumed | Execution plan V5.0, section 5 (synthetic)           |
| Emitter head A / B / C                                 | 10 / 9 / 10                      | m                       | assumed | Execution plan V5.0, section 5 (synthetic)           |
| Maximum zone flow A / B / C                            | 120 / 100 / 24                   | m3/h                    | assumed | Execution plan V5.0, section 5 (synthetic)           |
| Mainline length / diameter                             | 350, 350, 450 / 0.20             | m                       | assumed | Execution plan V5.0, section 5 (synthetic)           |
| Darcy friction factor (clean mainline)                 | 0.025                            | -                       | assumed | Execution plan V5.0, section 6.3                     |
| Shared gravity manifold A+B                            | 140                              | m3/h                    | assumed | Execution plan V5.0, section 5 (synthetic)           |
| Pump electrical limit / wire-to-water efficiency       | 3000 / 0.55                      | W / -                   | assumed | Execution plan V5.0, section 5 (synthetic)           |
| Reservoir capacity / initial / dead                    | 1500 / 900 / 50                  | m3                      | assumed | Execution plan V5.0, section 5 (synthetic)           |
| Reservoir floor / depth at capacity                    | +20.5 / 2.5                      | m                       | assumed | Chosen so the surface is +22 m at 900 m3             |
| Zone start margin above dead volume                    | 10                               | minutes of zone flow    | assumed | Prevents valve chatter near empty                    |
| TSE inflow daily mean                                  | 60                               | m3/h                    | assumed | Execution plan V5.0, section 5 (synthetic)           |
| TSE diurnal amplitude / peak hour                      | 25% / 14:00                      | - / h                   | assumed | Synthetic treatment-plant effluent profile           |
| Hydro recoverable inlet head / turbine efficiency      | 3 / 0.60                         | m / -                   | assumed | Execution plan V5.0, section 5 (synthetic)           |
| Solar array / derate                                   | 8 / 0.75                         | kWp / -                 | assumed | Execution plan V5.0, section 5 (synthetic)           |
| Solar profile                                          | sin(pi(h-6)/12)^1.2, 06:00-18:00 | -                       | assumed | Synthetic, not an irradiance forecast                |
| Battery capacity / initial SoC                         | 15 / 0.80                        | kWh / -                 | assumed | Execution plan V5.0, section 5 (synthetic)           |
| Battery cell floor / pump reserve                      | 0.10 / 0.20                      | SoC                     | assumed | Plan ruling 2                                        |
| Pump start margin above the reserve                    | 10                               | minutes of battery draw | assumed | Prevents pump chatter                                |
| Battery charge and discharge limit / efficiency        | 3000 / 0.95                      | W / -                   | assumed | Execution plan V5.0, section 5 (synthetic)           |
| Auxiliary load / flush load                            | 50 / 1200                        | W                       | assumed | Execution plan V5.0, section 5 (synthetic)           |
| Soil wilting point / field capacity / saturation       | 0.10 / 0.22 / 0.38               | m3/m3                   | assumed | Sandy-loam assumption                                |
| Root depth / crop coefficient / application efficiency | 0.8 / 0.85 / 0.90                | m / - / -               | assumed | Execution plan V5.0, section 5 (synthetic)           |
| Irrigation start threshold                             | 0.166                            | m3/m3                   | derived | FAO-56 RAW: fc - 0.45 (fc - wp)                      |
| Irrigation stop threshold                              | 0.198                            | m3/m3                   | derived | 0.90 x field capacity                                |
| Reference ET0 (nominal, seeded +/-10% per day)         | 4.9                              | mm/day                  | assumed | Constant fallback of plan section 6.2                |
| Filter pressure drop                                   | 12000 + 40000 x CI               | Pa                      | assumed | Illustrative, plan section 6.5                       |
| Filter loading per filtered m3                         | 3.5e-4                           | CI/m3                   | assumed | Chosen to flush about every 2 days at baseline       |
| Flush threshold / water / energy                       | 0.60 / 1.5 / 0.10                | CI / m3 / kWh           | assumed | Execution plan V5.0, section 5 (synthetic)           |
| Leaching allowance (fixed timer only)                  | 15                               | %                       | assumed | Scenario allowance, not salinity control             |
| Scheduler inventory / head margin / design clog        | 850 / 0.10 / 0.44                | m3 / m / CI             | assumed | RCA scheduling operating targets, not safety limits  |
| Scheduler pump power margin                            | 1                                | %                       | assumed | P0 avoids rated-flow envelope boundary               |
| Scheduler session / min run / rest                     | 30 / 10 / 10                     | min                     | assumed | Bounded sessions and restart hysteresis              |
| Scheduler restart inventory margin                     | 20                               | m3                      | assumed | Avoids inventory-boundary chatter                    |
| Scheduler battery operating / restart margin           | 0.35 / 0.02                      | SoC                     | assumed | RCA P0 operating margin; safety reserve remains 0.20 |
| Water-quality flag                                     | synthetic OK / HOLD / UNKNOWN    | -                       | assumed | Not an Egyptian regulatory compliance test           |

### Three sanity checks

Each is asserted in `backend/tests/test_physics.py`.

1. **Hydro is small.** 60 m³/h through a 3 m recoverable drop at 60% turbine efficiency gives **294 W**, not a 2 kW pump supply. The optimistic 18 m drop would give about 1.77 kW, but that drop is **unverified**.
2. **The uphill pump runs close to its limit.** Zone C at 24 m³/h needs 12 m of static lift from a +22 m reservoir surface, plus 10 m of emitter head, 0.13 m of mainline friction and 1.22 m across a clean filter. That is **23.35 m** of total dynamic head and **2.78 kW** at 55% wire-to-water efficiency. The same 24 m³/h at 28 m would need **3.33 kW**, beyond the 3 kW pump.
3. **Overflow is expected.** At 4.9 mm/day ET0 and Kc 0.85, the 15 ha canopy needs about **625 m³/day** net ET, while 60 m³/h of constant inflow brings **1,440 m³/day**. Reservoir overflow or diversion is part of the design, not a bug.

## The balances are part of the model

Every 60-second step must close four accounts:

| Account           | What must balance                                                                         |
| ----------------- | ----------------------------------------------------------------------------------------- |
| Reservoir         | Change in stored water = inflow − irrigation − flush − overflow.                          |
| Soil              | Change in root-zone water = infiltration − actual ET − drainage.                          |
| DC electrical bus | Hydro + solar + battery discharge + unserved load = loads + battery charge + curtailment. |
| Battery cells     | Change in stored energy = charge − discharge − losses.                                    |

Bounds and finite values are checked too. A mismatch raises with its step and inputs; the engine does not continue with invented numbers. See `backend/twin/engine.py` and `backend/tests/test_physics.py` for the assertions.

## Hard limits versus operating targets

The battery cell floor is 10% SoC; the hard pump reserve is 20%. Those are distinct checks. The experimental scheduler adds a 35% operating target and a 2% restart margin to its own budgeting, but these do not change the hard safety reserve or guarantee that a preset starts above the target.

Likewise, its nominal 850 m³ inventory target is not a fixed proof of hydraulic feasibility. The computed operating floor also considers filter loss and rated-flow head; it can exceed capacity. The scheduler must then wait, not lower the requirement to make the design appear viable.

Read [scheduler details](rca/scheduler.md) only if you need to inspect these operating rules. For what their trade-offs mean, use the [evidence guide](evidence-guide.md).

## What the model does not establish

Salinity transport, pathogens, tree growth, forest survival, carbon sequestration and a receiving-environment outlet are not modelled. The leaching allowance is a timer setting, not demonstrated salt control. A synthetic OK quality flag is not an Egyptian regulatory test.

Before any real reuse decision, replace assumptions with surveyed hydraulics, measured inflow/quality, soil and species data, calibrated energy performance and the necessary approvals. The model is useful for exploring dependencies before that work; it cannot substitute for it.

## References

- [FAO-56 Chapter 8](https://www.fao.org/4/X0490E/x0490e0e.htm): readily available soil water.
- [ISO 20419:2018](https://committee.iso.org/standard/67959.html): treated-wastewater irrigation and clogging.
- [Egyptian Standards Organization reference](https://www.eos.org.eg/en/standard/14743): ES 8174-1/2025.
- [Egyptian Code 501 reference](https://leap.unep.org/en/countries/eg/national-legislation/egyptian-code-no-5012005-use-treated-wastewater-agriculture): treated-wastewater reuse.

These are references for review, not a compliance determination. Verify current applicability with the competent authorities.
