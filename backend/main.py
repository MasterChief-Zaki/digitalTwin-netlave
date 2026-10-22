"""FastAPI routes for the twin: one process, one worker, one lock around every mutation.

There is no background ticking task. The browser advances the simulation with
`POST /advance` and awaits each reply, so pause is simply "send no more requests".
Run with `pnpm backend:dev` (uvicorn main:app --workers 1).
"""

import threading
from collections import deque

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import schemas
from config import SITE, SiteConfig
from twin.engine import EventDraft, step
from twin.state import SimState, new_run_state, to_snapshot

EVENT_HISTORY_LIMIT = 1000
EVENT_PAGE_LIMIT = 200


class StepConflict(Exception):
    def __init__(self, detail: schemas.ConflictDetail):
        super().__init__(detail.message)
        self.detail = detail


class TwinService:
    """The authoritative in-memory run, its generation counter and the event ledger."""

    def __init__(self, cfg: SiteConfig = SITE):
        self.cfg = cfg
        self.lock = threading.Lock()
        self.run_generation = 0
        self.latest_event_id = 0
        self.events: deque[schemas.Event] = deque(maxlen=EVENT_HISTORY_LIMIT)
        self.state: SimState = new_run_state(cfg, seed=7)
        self._load_run("baseline", 7, "SMART_HYSTERESIS")

    def snapshot(self) -> schemas.SimulationSnapshot:
        return to_snapshot(self.state, self.cfg, self.run_generation, self.latest_event_id)

    def advance(self, request: schemas.AdvanceRequest) -> schemas.AdvanceResponse:
        with self.lock:
            self._check_expected(request.run_generation, request.expected_step)
            new_events: list[schemas.Event] = []
            for _ in range(request.steps):
                result = step(self.state, self.cfg)
                self.state = result.state
                new_events.extend(self._record(result.state.step, draft) for draft in result.events)
            return schemas.AdvanceResponse(
                snapshot=self.snapshot(),
                events=new_events[-EVENT_PAGE_LIMIT:],
                events_truncated=len(new_events) > EVENT_PAGE_LIMIT,
                latest_event_id=self.latest_event_id,
            )

    def _load_run(
        self, scenario_id: schemas.ScenarioId, seed: int, control_policy: schemas.ControlPolicy
    ) -> None:
        self.run_generation += 1
        self.state = new_run_state(self.cfg, seed=seed, scenario_id=scenario_id, control_policy=control_policy)
        self._record(
            0,
            EventDraft("SCENARIO", None, "SCENARIO_LOADED", f"Loaded scenario {scenario_id} with seed {seed}."),
        )

    def _check_expected(self, run_generation: int, expected_step: int) -> None:
        if run_generation != self.run_generation or expected_step != self.state.step:
            raise StepConflict(
                schemas.ConflictDetail(
                    error_code="STEP_CONFLICT",
                    message="The run has moved on; refresh /state before sending more requests.",
                    current_step=self.state.step,
                    run_generation=self.run_generation,
                )
            )

    def _record(self, step_index: int, draft: EventDraft) -> schemas.Event:
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

    return app


app = create_app()
