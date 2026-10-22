// Display formatting only. Every value formatted here arrived in a snapshot.

const minutesPerDay = 24 * 60;

export function formatSimulatedClock(step: number, startHour: number): string {
  const totalMinutes = startHour * 60 + step;
  const day = Math.floor(totalMinutes / minutesPerDay) + 1;
  const minuteOfDay = totalMinutes % minutesPerDay;
  const hours = String(Math.floor(minuteOfDay / 60)).padStart(2, "0");
  const minutes = String(minuteOfDay % 60).padStart(2, "0");
  return `Day ${String(day)} · ${hours}:${minutes}`;
}

export function formatNumber(value: number, fractionDigits = 0): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
}

export function formatPercent(fraction: number, fractionDigits = 0): string {
  return `${formatNumber(fraction * 100, fractionDigits)}%`;
}

export function cubicMetresPerSecondToPerHour(flowM3S: number): number {
  return flowM3S * 3600;
}

export function joulesToKilowattHours(energyJ: number): number {
  return energyJ / 3.6e6;
}
