# Using the digital twin dashboard

Start with a question rather than a score: why did a zone receive water, wait, or stop? The dashboard shows a simulated request, the constraints it met, and the flow actually delivered.

All readings are from the Python model. **Live backend** means the browser is connected to the simulation service; it does not mean sensors are connected to a real forest.

## Load a run and move time

Use the header to choose a scenario, control policy and nonnegative seed, then press **Load run**. Changing a selector alone does not reset the model.

Loading a run returns to step 0 and starts a new run generation. The seed controls the model's reproducible input variation; it is not a site ID or a measured weather record. Existing events may still be visible because event IDs continue across resets for the server's lifetime. The chart window restarts for the new run.

| Control               | What it does                                                                                 |
| --------------------- | -------------------------------------------------------------------------------------------- |
| **Play**              | Repeatedly asks Python to advance, waiting for each reply.                                   |
| **Pause**             | Stops future advance requests. A request already in flight may still complete.               |
| **+1 min**            | Advances one 60-second step.                                                                 |
| **+1 h** / **+1 day** | Advances in batches of at most 60 steps until the requested interval is complete.            |
| **Speed**             | Changes steps per playback request: 1, 5, 15 or 60. It does not change the physics timestep. |

If another tab moves the shared run, the server rejects a stale request. The dashboard pauses playback and refreshes instead of applying an out-of-date reply. If the server is offline, controls depending on a live simulation are unavailable and the last displayed values are not new results.

## Choose a controller

- **Smart hysteresis:** the default. Requests water after moisture crosses below 0.166 m³/m³ and continues until it reaches 0.198 m³/m³.
- **Fixed timer:** daily windows sized using nominal ET demand, application efficiency and a leaching allowance. It is a meaningful baseline, not an intentionally wasteful schedule.
- **Resource aware (experimental, opt-in):** starts from hysteresis demand and schedules bounded automatic sessions against current storage, head and energy. It may defer a request before it reaches safety resolution.

The experimental scheduler has not passed every declared held-out service check. Its lower raw delivery must not be described as validated savings. See the [evidence guide](evidence-guide.md).

**Auto / Open / Close** on a zone are manual control modes, separate from the policy selector. Open is still a request: quality, filter, storage, head, manifold and electrical limits can deny it. Close stops that zone's request; it does not turn the whole system into a new policy.

## Read the panels in order

### 1. Readings: what is happening now?

The tiles show current flow, moisture, power, battery charge and filter state. Some also show a cumulative total since the run or measurement accounts began.

Check units carefully:

- **m³/h:** a flow rate now; **m³:** a volume accumulated over time.
- **W:** power now; **kWh:** energy accumulated over time.
- **m³/m³:** volumetric soil moisture, not a percentage of reservoir capacity.
- **SoC:** battery state of charge.

ET service and electrical autonomy can show **Pending** before their denominators contain enough simulated activity. That is not an error or a missing sensor.

Electrical autonomy refers to **admitted loads**. If the resolver excludes the pump because its request cannot be powered, the admitted-load score can remain high while irrigation service suffers. Read the zone service ledger alongside it.

### 2. Site: connect the picture to the readings

The isometric view is a schematic, not a surveyed plan. Water-direction markers follow delivered flows, not merely valve requests. Energy paths follow generation, charging, discharging and admitted pump power. Reservoir elevation and battery fill come from snapshots.

The view distinguishes Active, Idle, Waiting and Fault states. Click a terrace or use its zone button to select the same zone as the dashboard. Without WebGL2, the readings and accessible selection still work.

Tree color is only the model's moisture-stress proxy. It does not measure growth, survival, species condition or carbon.

### 3. Zones: request versus delivery

For a selected zone, compare:

1. **Requested flow:** what control wants.
2. **Delivered flow:** what the resolver grants.
3. **Head available versus needed:** whether pressure and elevation can support the rated flow.
4. **Reason and explanation:** why the action was accepted, deferred or denied.

A request with zero delivery is useful information, not a broken animation. In the baseline, B initially waits because A and B cannot both use their full rated gravity flows through the shared manifold.

### 4. Faults: change an input, then advance

The fault controls change synthetic cloud, solids, inflow or water-quality settings. They do not write arbitrary reservoir volume, battery energy or soil moisture. Advance the run to see the physical consequence.

HOLD and UNKNOWN quality flags block irrigation. They stand in for a synthetic safety input, not a laboratory result or Egyptian reuse authorization.

### 5. Trends, ledger and events: what happened over time?

Charts show a bounded recent history of snapshots, not a saved telemetry archive. Fast-forwarding adds samples after each response; it does not plot every minute in a long batch.

The ledger records water and energy totals plus zone service. Read actual/potential ET and deficit with initial/final soil storage. Less delivered water may simply mean a zone used stored soil water or went under-served.

The repeated denied-request integral is not a unique crop-shortage measurement. A request can be denied repeatedly across many steps. The ET deficit is a separate modelled adequacy proxy.

Events explain commands, denials, flushes and overflow. The visible feed is bounded; long advances can truncate older events. Reloading the page or restarting the backend is not a way to preserve a run.

## Try the four presets

Keep smart hysteresis selected for the documented first-step behavior.

| Preset                    | What to look for                                                                                                                                 |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Baseline**              | A and C start; B waits on the 140 m³/h gravity manifold.                                                                                         |
| **Clogged filter**        | Solids ×8 reduces B's head while A runs. A five-minute flush starts at clog index 0.60, uses 1.5 m³ and 0.10 kWh, and allows service to recover. |
| **Low solar (sandstorm)** | Cloud factor 0.25 and starting battery 24%. C's pump runs about 13 minutes, then stops at the hard 20% reserve.                                  |
| **TSE interruption**      | Day-one inflow stops from 06:30 to 12:30. Hydro becomes zero and storage draws down; low-storage denial happens only if its gate is reached.     |

These presets deliberately use demo starting conditions so consequences appear quickly. They are not measured steady states from a plantation. Loading the experimental scheduler can change the response because it may defer requests upstream of safety.

## Run an experiment without moving the live run

The Experiment panel runs private Python states. It uses the loaded scenario and seed, not the current evolved reservoir/soil/battery state or a snapshot of every operator fault you just toggled. Playback and the live clock are not reset by the comparison.

- Leave **Matched operation** unchecked for a startup-inclusive comparison from the preset.
- Check it for common 10-day fixed-timer warm-up before scoring the selected number of days. The TSE outage moves into that measured window.
- Check **Include experimental scheduler** to add its report alongside fixed timer and hysteresis.
- Choose **Days** from 1 to 30 and press **Run A/B**. Wait for it to finish; a longer model run takes longer to compute.

The dashboard is a single-seed diagnostic, even in matched-operation mode. Published release evidence uses a separate held-out batch protocol. “Matching digests” means matching input/initial-state descriptions, not proof of real-world accuracy or validated savings.

For interpretation, continue with [evidence guide](evidence-guide.md). For a failed connection or old schema, use [troubleshooting](development-troubleshooting.md). For implementation details, use [architecture and API](architecture-and-api.md).
