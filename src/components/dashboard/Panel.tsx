import type { ReactNode } from "react";
import { classNames } from "@/lib/classNames";
import styles from "./Panel.module.scss";

interface PanelProps {
  label: string;
  title: string;
  headingId: string;
  actions?: ReactNode;
  className?: string;
  children: ReactNode;
}

// A dashboard card with the landing page's mono dash label above its heading.
export function Panel({
  label,
  title,
  headingId,
  actions,
  className,
  children,
}: PanelProps) {
  return (
    <section
      className={classNames(styles.panel, className)}
      aria-labelledby={headingId}
    >
      <header className={styles.panelHeader}>
        <div>
          <p className={styles.panelLabel}>{label}</p>
          <h2 id={headingId} className={styles.panelTitle}>
            {title}
          </h2>
        </div>
        {actions}
      </header>
      {children}
    </section>
  );
}
