"use client";

import { useState } from "react";
import { classNames } from "@/lib/classNames";
import { formatSimulatedClock } from "@/lib/format";
import { reasonPresentation, toneSymbol } from "@/lib/reasonCodes";
import { useTwinStore } from "@/store/useTwinStore";
import { Panel } from "./Panel";
import styles from "./Events.module.scss";

export function Events() {
  const events = useTwinStore((state) => state.events);
  const startHour = useTwinStore((state) => state.snapshot.start_hour);
  const [denialsOnly, setDenialsOnly] = useState(false);

  const visibleEvents = events
    .filter((event) => !denialsOnly || event.category === "DENIAL")
    .slice()
    .reverse();

  return (
    <Panel
      label="06 — Events"
      title="Decision log"
      headingId="events-heading"
      className={styles.eventsPanel}
      actions={
        <label className={styles.filter}>
          <input
            type="checkbox"
            checked={denialsOnly}
            onChange={(event) => {
              setDenialsOnly(event.target.checked);
            }}
          />
          Denials only
        </label>
      }
    >
      {visibleEvents.length === 0 ? (
        <p className={styles.empty}>
          No events yet. Start the backend and press Play.
        </p>
      ) : (
        <ol className={styles.feed} aria-live="polite">
          {visibleEvents.map((event) => {
            const presentation = reasonPresentation[event.reason_code];
            return (
              <li key={event.id} className={styles.event}>
                <p className={styles.eventMeta}>
                  <span
                    className={classNames(
                      styles.eventTone,
                      styles[presentation.tone],
                    )}
                  >
                    <span aria-hidden="true">
                      {toneSymbol[presentation.tone]}
                    </span>{" "}
                    {presentation.label}
                  </span>
                  {event.zone_id ? (
                    <span className={styles.eventZone}>
                      Zone {event.zone_id}
                    </span>
                  ) : null}
                  <span className={styles.eventTime}>
                    {formatSimulatedClock(event.step, startHour)} · #{event.id}
                  </span>
                </p>
                <p className={styles.eventMessage}>{event.message}</p>
              </li>
            );
          })}
        </ol>
      )}
    </Panel>
  );
}
