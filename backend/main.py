"""FastAPI routes for the twin: one process, one worker, one lock around every mutation.

There is no background ticking task. The browser advances the simulation with
`POST /advance` and awaits each reply, so pause is simply "send no more requests".
Run with `pnpm backend:dev` (uvicorn main:app --workers 1).
"""

import hashlib
import json
import threading
from collections import OrderedDict, deque
from dataclasses import asdict

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

import schemas
from config import ASSUMPTIONS, SITE, SiteConfig
from scenarios.comparison import run_comparison
from scenarios.presets import SCENARIOS, build_scenario
from twin.engine import EventDraft, step
from twin.state import SimState, to_snapshot

EVENT_HISTORY_LIMIT = 1000
EVENT_PAGE_LIMIT = 200
IDEMPOTENCY_LEDGER_LIMIT = 256


class StepConflict(Exception):
    def __init__(self, detail: schemas.ConflictDetail):
        super().__init__(detail.message)
        self.detail = detail


class TwinService:
    """The authoritative in-memory run, its generation counter, the event ledger and the idempotency ledger."""

    def __init__(self, cfg: SiteConfig = SITE):
        self.cfg = cfg
        self.lock = threading.Lock()
        self.run_generation = 0
        self.latest_event_id = 0
        self.events: deque[schemas.Event] = deque(maxlen=EVENT_HISTORY_LIMIT)
        # (run_generation, request_id) -> (request payload hash, cached reply)
        self.replies: OrderedDict[tuple[int, str], tuple[str, schemas.AdvanceResponse]] = OrderedDict()
        self.state: SimState = build_scenario(cfg, "baseline", seed=7)
        self._load_run("baseline", 7, "SMART_HYSTERESIS")

    def snapshot(self) -> schemas.SimulationSnapshot:
        with self.lock:
            return self._snapshot()

    def advance(self, request: schemas.AdvanceRequest) -> schemas.AdvanceResponse:
        with self.lock:
            key = (request.run_generation, request.request_id)
            payload_hash = _payload_hash(request)
            cached = self.replies.get(key)
            if cached is not None:
                if cached[0] != payload_hash:
                    raise self._conflict("IDEMPOTENCY_CONFLICT", "This request_id was already used with other arguments.")
                return cached[1]
            self._check_expected(request.run_generation, request.expected_step)

            new_events: list[schemas.Event] = []
            for _ in range(request.steps):
                result = step(self.state, self.cfg)
                self.state = result.state
                new_events.extend(self._record(result.state.step, draft) for draft in result.events)
            reply = schemas.AdvanceResponse(
                snapshot=self._snapshot(),
                events=new_events[-EVENT_PAGE_LIMIT:],
                events_truncated=len(new_events) > EVENT_PAGE_LIMIT,
                latest_event_id=self.latest_event_id,
            )
            self.replies[key] = (payload_hash, reply)
            if len(self.replies) > IDEMPOTENCY_LEDGER_LIMIT:
                self.replies.popitem(last=False)
            return reply

    def command(self, request: schemas.CommandRequest) -> schemas.SimulationSnapshot:
        with self.lock:
            self._check_expected(request.run_generation, request.expected_step)
            message = _apply_command(self.state, request.command)
            zone_id = request.command.zone_id if isinstance(request.command, schemas.SetZoneModeCommand) else None
            self._record(self.state.step, EventDraft("COMMAND", zone_id, "OPERATOR_COMMAND", message))
            return self._snapshot()

    def reset(self, request: schemas.ResetRequest) -> schemas.SimulationSnapshot:
        with self.lock:
            self._load_run(request.scenario_id, request.seed, request.control_policy)
            return self._snapshot()

    def events_since(self, since_id: int) -> schemas.EventsPage:
        with self.lock:
            oldest_retained_id = self.events[0].id if self.events else self.latest_event_id + 1
            return schemas.EventsPage(
                events=[event for event in self.events if event.id > since_id],
                latest_event_id=self.latest_event_id,
                history_truncated=since_id < oldest_retained_id - 1,
            )

    def _snapshot(self) -> schemas.SimulationSnapshot:
        return to_snapshot(self.state, self.cfg, self.run_generation, self.latest_event_id)

    def _load_run(
        self, scenario_id: schemas.ScenarioId, seed: int, control_policy: schemas.ControlPolicy
    ) -> None:
        """A fresh run: late requests from the previous generation can no longer mutate it."""
        self.run_generation += 1
        self.replies.clear()
        self.state = build_scenario(self.cfg, scenario_id, seed=seed, control_policy=control_policy)
        policy_name = "smart hysteresis" if control_policy == "SMART_HYSTERESIS" else "fixed timer"
        self._record(
            0,
            EventDraft(
                "SCENARIO",
                None,
                "SCENARIO_LOADED",
                f"Loaded scenario {scenario_id} (seed {seed}, {policy_name} control).",
            ),
        )

    def _check_expected(self, run_generation: int, expected_step: int) -> None:
        if run_generation != self.run_generation or expected_step != self.state.step:
            raise self._conflict("STEP_CONFLICT", "The run has moved on; refresh /state before sending more requests.")

    def _conflict(self, error_code: str, message: str) -> StepConflict:
        return StepConflict(
            schemas.ConflictDetail(
                error_code=error_code,
                message=message,
                current_step=self.state.step,
                run_generation=self.run_generation,
            )
        )

    def _record(self, step_index: int, draft: EventDraft) -> schemas.Event:
        """Event IDs grow monotonically for the server's lifetime, across resets."""
        self.latest_event_id += 1
        event = schemas.Event(
            id=self.latest_event_id,
            step=step_index,
            category=draft.category,
            zone_id=draft.zone_id,
            reason_code=draft.reason_code,
            message=draft.message,
        )
        self.events.append(event)
        return event


def _payload_hash(request: schemas.AdvanceRequest) -> str:
    return hashlib.sha256(json.dumps(request.model_dump(), sort_keys=True).encode("utf-8")).hexdigest()


def _apply_command(state: SimState, command: schemas.Command) -> str:
    """Operator commands change control settings or the environment, never physical state."""
    environment = state.environment
    if isinstance(command, schemas.SetZoneModeCommand):
        zone = next(zone for zone in state.zones if zone.zone_id == command.zone_id)
        zone.control_mode = command.mode
        return f"Operator set zone {command.zone_id} to {command.mode.replace('_', ' ').lower()}."
    if isinstance(command, schemas.SetWaterQualityCommand):
        environment.water_quality = command.status
        return f"Operator set the synthetic TSE quality flag to {command.status}."
    if isinstance(command, schemas.SetCloudFactorCommand):
        environment.cloud_factor = command.cloud_factor
        return f"Operator set the cloud factor to {command.cloud_factor:.2f}."
    if isinstance(command, schemas.SetSolidsMultiplierCommand):
        environment.solids_loading_multiplier = command.multiplier
        return f"Operator set the filter solids loading to {command.multiplier:g}x."
    environment.inflow_available = command.available
    return "Operator restored the TSE inflow." if command.available else "Operator cut the TSE inflow."


def create_app(cfg: SiteConfig = SITE) -> FastAPI:
    app = FastAPI(title="netLave Digital Twin", version=schemas.SCHEMA_VERSION)
    service = TwinService(cfg)

    @app.exception_handler(StepConflict)
    def step_conflict_handler(_request: Request, conflict: StepConflict) -> JSONResponse:
        return JSONResponse(status_code=409, content=conflict.detail.model_dump())

    @app.get("/state")
    def get_state() -> schemas.SimulationSnapshot:
        return service.snapshot()

    @app.post("/advance")
    def post_advance(request: schemas.AdvanceRequest) -> schemas.AdvanceResponse:
        return service.advance(request)

    @app.post("/command")
    def post_command(request: schemas.CommandRequest) -> schemas.SimulationSnapshot:
        return service.command(request)

    @app.post("/reset")
    def post_reset(request: schemas.ResetRequest) -> schemas.SimulationSnapshot:
        return service.reset(request)

    @app.get("/events")
    def get_events(since_id: int = Query(default=0, ge=0)) -> schemas.EventsPage:
        return service.events_since(since_id)

    @app.get("/scenarios")
    def get_scenarios() -> schemas.ScenariosResponse:
        return schemas.ScenariosResponse(
            scenarios=[
                schemas.ScenarioInfo(
                    id=scenario.id,
                    title=scenario.title,
                    description=scenario.description,
                    demo_initial_conditions=scenario.demo_initial_conditions,
                )
                for scenario in SCENARIOS
            ],
            assumptions=[
                schemas.AssumptionRow(
                    name=row.name, value=row.value, unit=row.unit, status=row.status, source=row.source
                )
                for row in ASSUMPTIONS
            ],
        )

    @app.post("/compare")
    def post_compare(request: schemas.CompareRequest) -> schemas.CompareResponse:
        """A headless A/B run on private states; it never takes the live run's lock or touches it."""
        report = run_comparison(cfg, request.scenario_id, request.seed, request.horizon_days)
        return schemas.CompareResponse(
            data_mode="SIMULATED",
            scenario_id=report.scenario_id,
            seed=report.seed,
            horizon_days=report.horizon_days,
            steps=report.steps,
            fixed_timer=schemas.PolicyReport(**asdict(report.fixed_timer)),
            smart_hysteresis=schemas.PolicyReport(**asdict(report.smart_hysteresis)),
            water_savings_fraction=report.water_savings_fraction,
            elapsed_s=report.elapsed_s,
        )

    return app


app = create_app()
