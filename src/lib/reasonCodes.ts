import type { ReasonCode } from "@/types/simulation";

export type StatusTone = "active" | "idle" | "warning" | "fault";

interface ReasonPresentation {
  label: string;
  tone: StatusTone;
}

// Plain-English labels and a status tone for every frozen reason code.
export const reasonPresentation: Record<ReasonCode, ReasonPresentation> = {
  SOIL_BELOW_THRESHOLD: { label: "Soil below trigger", tone: "active" },
  KEEP_OPEN: { label: "Irrigating", tone: "active" },
  KEEP_CLOSED: { label: "No demand", tone: "idle" },
  MANUAL_OVERRIDE_OK: { label: "Manual open", tone: "active" },
  MANUAL_STOP_OK: { label: "Manual stop", tone: "idle" },
  WATER_QUALITY_HOLD: { label: "Quality hold", tone: "fault" },
  FLUSH_IN_PROGRESS: { label: "Flush in progress", tone: "warning" },
  FILTER_FLUSH_REQUIRED: { label: "Flush required", tone: "warning" },
  RESERVOIR_LOW: { label: "Reservoir low", tone: "fault" },
  INSUFFICIENT_HEAD: { label: "Insufficient head", tone: "fault" },
  CONCURRENT_FLOW_LIMIT: { label: "Manifold busy", tone: "warning" },
  POWER_DEFICIT: { label: "Power deficit", tone: "fault" },
  BATTERY_BELOW_RESERVE: { label: "Battery at reserve", tone: "fault" },
  AUX_POWER_OUTAGE: { label: "Aux power outage", tone: "fault" },
  FILTER_FLUSH_STARTED: { label: "Flush started", tone: "warning" },
  FILTER_FLUSH_COMPLETE: { label: "Flush complete", tone: "active" },
  OVERFLOW_OCCURRING: { label: "Overflow", tone: "warning" },
  SCENARIO_LOADED: { label: "Scenario loaded", tone: "idle" },
  MOISTURE_TARGET_REACHED: { label: "Target reached", tone: "idle" },
  SCHEDULE_WINDOW_OPEN: { label: "Timer window open", tone: "active" },
  SCHEDULE_WINDOW_CLOSED: { label: "Timer window closed", tone: "idle" },
  OPERATOR_COMMAND: { label: "Operator command", tone: "idle" },
  SCHEDULER_WATER_HOLD: { label: "Inventory/head deferral", tone: "warning" },
  SCHEDULER_ENERGY_HOLD: { label: "Energy budget deferral", tone: "warning" },
  SCHEDULER_QUEUE: { label: "Queued session", tone: "warning" },
  SCHEDULER_REST: { label: "Session rest", tone: "idle" },
};

export const toneSymbol: Record<StatusTone, string> = {
  active: "●",
  idle: "○",
  warning: "▲",
  fault: "■",
};
