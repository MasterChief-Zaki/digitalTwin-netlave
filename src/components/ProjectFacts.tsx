import Link from "next/link";
import truth from "@/content/ground-truth.json";
import styles from "./ProjectFacts.module.scss";

export function ProjectFacts() {
  return (
    <section className={styles.facts} aria-labelledby="project-facts-heading">
      <h2 id="project-facts-heading">NetLave: the shared project facts</h2>
      <p>{truth.description}</p>
      <p>{truth.claimLimit}</p>
      <p>{truth.controllerStatus}</p>
      <Link href="/ground-truth">
        Read the assumptions, evidence and safety boundaries →
      </Link>
    </section>
  );
}
