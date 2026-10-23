# Experimental resource-aware scheduler

`SMART_RESOURCE_AWARE` is opt-in. The original default and safety resolver stay
unchanged. All operating assumptions are in `SchedulerConfig` and the served
assumption table, not hard-coded simulated results.

The demand signal remains moisture hysteresis. The scheduler arbitrates bounded
30-minute automatic sessions, one at a time. Ten-minute normal minimum runs,
ten-minute rests and inventory/SoC restart margins limit chatter. Waiting steps
rank ahead of stress after a minimum run; thus a wet/easy zone cannot monopolize
service. Safety can interrupt at any time. Manual requests skip scheduling but
never safety resolution.

The floor is computed each step from the greater of actual/design filter clog
at rated zone flows. Inverting the existing linear surface-volume relation gives
the storage needed for each gravity margin and pump envelope. A required floor
above reservoir capacity means the design condition is unschedulable, not a
reason to clamp the requirement down. Projected session withdrawal must remain
above the operating floor (and restart margin); admitted energy must fit the
operating battery margin. Neither current inflow nor future solar is credited as
an assured refill. This is intentionally conservative, and its service cost must
be measured rather than described as an efficiency gain.

Pauses preserve the session's remaining volume and latch. Paused minutes count
as scheduling deferral; submitted but rejected requests count as safety denial.
These are mutually exclusive. Pause/resume/session counters expose behavior
that could otherwise disappear behind aggregate demand totals. Stopped demand
completes/cancels a session; manual mode does not inherit automatic budgets.

Water-only ablation uses `energy_aware=False` in a separate configuration; it is
not another public control policy. Validation must compare it on matched hardware
and inputs, alongside the combined scheduler, with separate reports. The
35% SoC operating target is not a physical minimum when an initial preset is
already below 35%; low-solar preset starts at 24%. No default promotion is enabled
by code, sign counts or single-seed results.
