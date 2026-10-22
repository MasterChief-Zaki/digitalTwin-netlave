"""The safety resolver: the only place irrigation is granted.

Requests that want water pass the gates in the documented order; the first
failing gate denies the whole request (no fabricated partial flow without a
pump curve). Stop and keep-closed requests are always granted and need no
water or energy. A manual open never bypasses a gate.
"""

from dataclasses import dataclass

import schemas
from config import SiteConfig
from control.policy import ZoneRequest


@dataclass(frozen=True)
class Grant:
    zone_id: str
    action: schemas.RequestedAction
    accepted: bool
    reason_code: schemas.ReasonCode
    explanation: str
    flow_m3_s: float
    requested_flow_m3_s: float


@dataclass
class SafetyContext:
    dt_s: int
    usable_volume_m3: float
    committed_withdrawal_m3: float = 0.0


def resolve(ranked_requests: list[ZoneRequest], context: SafetyContext, cfg: SiteConfig) -> dict[str, Grant]:
    grants: dict[str, Grant] = {}
    for request in ranked_requests:
        if not request.wants_water:
            grants[request.zone_id] = _grant(request, request.reason_code, request.explanation)
            continue
        denial = _reservoir_gate(request, context)
        if denial is not None:
            grants[request.zone_id] = _deny(request, *denial)
            continue
        context.committed_withdrawal_m3 += request.flow_m3_s * context.dt_s
        grants[request.zone_id] = _grant(request, request.reason_code, request.explanation, request.flow_m3_s)
    return grants


Denial = tuple[schemas.ReasonCode, str]


def _reservoir_gate(request: ZoneRequest, context: SafetyContext) -> Denial | None:
    needed_m3 = request.flow_m3_s * context.dt_s
    remaining_m3 = context.usable_volume_m3 - context.committed_withdrawal_m3
    if needed_m3 > remaining_m3:
        return (
            "RESERVOIR_LOW",
            f"Zone {request.zone_id} needs {needed_m3:.2f} m3 this minute but only {max(0.0, remaining_m3):.2f} m3 "
            "is above the reservoir's dead volume.",
        )
    return None


def _grant(
    request: ZoneRequest, reason_code: schemas.ReasonCode, explanation: str, flow_m3_s: float = 0.0
) -> Grant:
    return Grant(request.zone_id, request.action, True, reason_code, explanation, flow_m3_s, request.flow_m3_s)


def _deny(request: ZoneRequest, reason_code: schemas.ReasonCode, explanation: str) -> Grant:
    return Grant(request.zone_id, request.action, False, reason_code, explanation, 0.0, request.flow_m3_s)
