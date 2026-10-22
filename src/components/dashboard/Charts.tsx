"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TooltipContentProps } from "recharts";
import { formatNumber, formatSimulatedClock } from "@/lib/format";
import { useEffect, useState } from "react";
import { useTwinStore } from "@/store/useTwinStore";
import type { ChartPoint } from "@/store/useTwinStore";
import { Panel } from "./Panel";
import styles from "./Charts.module.scss";

type SeriesKey = Exclude<keyof ChartPoint, "step">;

interface SeriesSpec {
  dataKey: SeriesKey;
  name: string;
  color: string;
}

interface ReferenceSpec {
  value: number;
  label: string;
}

interface TimeSeriesChartProps {
  title: string;
  unit: string;
  fractionDigits: number;
  series: SeriesSpec[];
  points: ChartPoint[];
  startHour: number;
  yDomain?: [number, number];
  references?: ReferenceSpec[];
}

// Recharts costs tens of milliseconds per render however few points it draws,
// so the charts redraw at most once a second instead of on every simulation tick.
const chartRefreshIntervalMs = 1000;

function useThrottledChartPoints(intervalMs: number): ChartPoint[] {
  const [points, setPoints] = useState(
    () => useTwinStore.getState().chartPoints,
  );

  useEffect(() => {
    let lastRefresh = 0;
    let pendingRefresh: ReturnType<typeof setTimeout> | undefined;
    const refresh = () => {
      pendingRefresh = undefined;
      lastRefresh = performance.now();
      setPoints(useTwinStore.getState().chartPoints);
    };
    const unsubscribe = useTwinStore.subscribe((state, previous) => {
      if (
        state.chartPoints === previous.chartPoints ||
        pendingRefresh !== undefined
      ) {
        return;
      }
      const sinceLastRefresh = performance.now() - lastRefresh;
      pendingRefresh = setTimeout(
        refresh,
        Math.max(0, intervalMs - sinceLastRefresh),
      );
    });
    return () => {
      unsubscribe();
      if (pendingRefresh !== undefined) {
        clearTimeout(pendingRefresh);
      }
    };
  }, [intervalMs]);

  return points;
}

const axisTick = {
  fill: "var(--color-text-muted)",
  fontSize: 11,
  fontFamily: "var(--font-family-mono)",
};

function TimeSeriesChart({
  title,
  unit,
  fractionDigits,
  series,
  points,
  startHour,
  yDomain,
  references = [],
}: TimeSeriesChartProps) {
  const latest = points.at(-1);
  const formatValue = (value: number) =>
    `${formatNumber(value, fractionDigits)} ${unit}`;

  function renderTooltip({ active, payload, label }: TooltipContentProps) {
    if (!active || payload.length === 0) {
      return null;
    }
    return (
      <div className={styles.tooltip}>
        <p className={styles.tooltipTime}>
          {formatSimulatedClock(Number(label), startHour)}
        </p>
        {payload.map((entry) => (
          <p key={String(entry.dataKey)} className={styles.tooltipRow}>
            <span
              className={styles.legendKey}
              style={{ background: entry.color }}
              aria-hidden="true"
            />
            {entry.name}
            <span className={styles.tooltipValue}>
              {formatValue(Number(entry.value))}
            </span>
          </p>
        ))}
      </div>
    );
  }

  return (
    <figure className={styles.chart}>
      <figcaption className={styles.chartHeader}>
        <span className={styles.chartTitle}>
          {title} <span className={styles.chartUnit}>({unit})</span>
        </span>
        {series.length > 1 ? (
          <ul className={styles.legend}>
            {series.map((spec) => (
              <li key={spec.dataKey} className={styles.legendItem}>
                <span
                  className={styles.legendKey}
                  style={{ background: spec.color }}
                  aria-hidden="true"
                />
                {spec.name}
                {latest ? (
                  <span className={styles.legendValue}>
                    {formatNumber(latest[spec.dataKey], fractionDigits)}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        ) : null}
      </figcaption>
      <div className={styles.plot}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={points}
            margin={{ top: 8, right: 28, bottom: 0, left: 0 }}
          >
            <CartesianGrid
              stroke="var(--color-border)"
              strokeOpacity={0.45}
              vertical={false}
            />
            <XAxis
              dataKey="step"
              type="number"
              domain={["dataMin", "dataMax"]}
              tick={axisTick}
              tickFormatter={(step: number) =>
                formatSimulatedClock(step, startHour).replace("Day ", "D")
              }
              stroke="var(--color-border)"
              minTickGap={40}
            />
            <YAxis
              tick={axisTick}
              stroke="var(--color-border)"
              width={52}
              domain={yDomain ?? ["auto", "auto"]}
              tickFormatter={(value: number) =>
                formatNumber(value, fractionDigits)
              }
            />
            {references.map((reference) => (
              <ReferenceLine
                key={reference.label}
                y={reference.value}
                stroke="var(--color-text-muted)"
                strokeDasharray="4 4"
                strokeOpacity={0.7}
                label={{
                  value: reference.label,
                  position: "insideTopRight",
                  ...axisTick,
                }}
              />
            ))}
            <Tooltip
              content={renderTooltip}
              cursor={{ stroke: "var(--color-text-muted)", strokeWidth: 1 }}
            />
            {series.map((spec) => (
              <Line
                key={spec.dataKey}
                dataKey={spec.dataKey}
                name={spec.name}
                stroke={spec.color}
                strokeWidth={2}
                dot={false}
                activeDot={{
                  r: 4,
                  stroke: "var(--color-surface)",
                  strokeWidth: 2,
                }}
                isAnimationActive={false}
                type="linear"
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}

function ChartDataTable({
  points,
  startHour,
}: {
  points: ChartPoint[];
  startHour: number;
}) {
  const recentPoints = points.slice(-12).reverse();
  return (
    <details className={styles.dataTable}>
      <summary>Show the latest chart values as a table</summary>
      <div className={styles.tableScroll}>
        <table>
          <thead>
            <tr>
              <th scope="col">Simulated time</th>
              <th scope="col">A m³/m³</th>
              <th scope="col">B m³/m³</th>
              <th scope="col">C m³/m³</th>
              <th scope="col">Reservoir m³</th>
              <th scope="col">Solar W</th>
              <th scope="col">Hydro W</th>
              <th scope="col">Pump W</th>
            </tr>
          </thead>
          <tbody>
            {recentPoints.map((point) => (
              <tr key={point.step}>
                <th scope="row">
                  {formatSimulatedClock(point.step, startHour)}
                </th>
                <td>{formatNumber(point.zoneAMoisture, 3)}</td>
                <td>{formatNumber(point.zoneBMoisture, 3)}</td>
                <td>{formatNumber(point.zoneCMoisture, 3)}</td>
                <td>{formatNumber(point.reservoirVolumeM3)}</td>
                <td>{formatNumber(point.solarPowerW)}</td>
                <td>{formatNumber(point.hydroPowerW)}</td>
                <td>{formatNumber(point.pumpPowerW)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

export function Charts() {
  const points = useThrottledChartPoints(chartRefreshIntervalMs);
  // Primitive selections, so a new snapshot alone doesn't redraw the charts.
  const startHour = useTwinStore((state) => state.snapshot.start_hour);
  const moistureTrigger = useTwinStore(
    (state) => state.snapshot.zones[0]?.moisture_trigger_m3_m3,
  );
  const moistureTarget = useTwinStore(
    (state) => state.snapshot.zones[0]?.moisture_target_m3_m3,
  );
  const capacityM3 = useTwinStore(
    (state) => state.snapshot.reservoir.capacity_m3,
  );
  const deadVolumeM3 = useTwinStore(
    (state) => state.snapshot.reservoir.dead_volume_m3,
  );

  return (
    <Panel
      label="04 — Trends"
      title="Water and energy over simulated time"
      headingId="charts-heading"
      className={styles.chartsPanel}
    >
      <div className={styles.chartGrid}>
        <TimeSeriesChart
          title="Soil moisture"
          unit="m³/m³"
          fractionDigits={3}
          points={points}
          startHour={startHour}
          series={[
            {
              dataKey: "zoneAMoisture",
              name: "Zone A",
              color: "var(--color-series-zone-a)",
            },
            {
              dataKey: "zoneBMoisture",
              name: "Zone B",
              color: "var(--color-series-zone-b)",
            },
            {
              dataKey: "zoneCMoisture",
              name: "Zone C",
              color: "var(--color-series-zone-c)",
            },
          ]}
          references={
            moistureTrigger !== undefined && moistureTarget !== undefined
              ? [
                  { value: moistureTrigger, label: "start" },
                  { value: moistureTarget, label: "stop" },
                ]
              : []
          }
        />
        <TimeSeriesChart
          title="Reservoir volume"
          unit="m³"
          fractionDigits={0}
          points={points}
          startHour={startHour}
          yDomain={[0, capacityM3]}
          series={[
            {
              dataKey: "reservoirVolumeM3",
              name: "Reservoir",
              color: "var(--color-accent)",
            },
          ]}
          references={[
            { value: capacityM3, label: "capacity" },
            { value: deadVolumeM3, label: "dead volume" },
          ]}
        />
        <TimeSeriesChart
          title="Generation and pumping"
          unit="W"
          fractionDigits={0}
          points={points}
          startHour={startHour}
          series={[
            {
              dataKey: "solarPowerW",
              name: "Solar",
              color: "var(--color-series-solar)",
            },
            {
              dataKey: "hydroPowerW",
              name: "Hydro",
              color: "var(--color-series-hydro)",
            },
            {
              dataKey: "pumpPowerW",
              name: "Pump C",
              color: "var(--color-series-pump)",
            },
          ]}
        />
      </div>
      <ChartDataTable points={points} startHour={startHour} />
    </Panel>
  );
}
