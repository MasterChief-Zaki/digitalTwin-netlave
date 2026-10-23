import Image from "next/image";
import Link from "next/link";
import truth from "@/content/ground-truth.json";
import { pageMetadata } from "@/lib/seo";
import styles from "./page.module.scss";

export const metadata = pageMetadata(
  "NetLave ground truth: assumptions, evidence and safety",
  "/ground-truth",
);

const facts = [
  [
    "Forest area",
    `${String(truth.siteAssumptions.forestAreaHa)} ha across three zones`,
  ],
  [
    "Reservoir",
    `${String(truth.siteAssumptions.reservoirCapacityM3)} m³ capacity; ${String(truth.siteAssumptions.initialReservoirM3)} m³ initially`,
  ],
  ["Mean TSE inflow", `${String(truth.siteAssumptions.meanInflowM3Hour)} m³/h`],
  [
    "Solar and battery",
    `${String(truth.siteAssumptions.solarCapacityKwp)} kWp; ${String(truth.siteAssumptions.batteryCapacityKwh)} kWh`,
  ],
  [
    "Uphill pump",
    `${String(truth.siteAssumptions.pumpLimitKw)} kW electrical limit; 20% battery reserve`,
  ],
  [
    "Micro-hydro",
    `About ${String(truth.siteAssumptions.hydroPowerW)} W at the assumed ${String(truth.siteAssumptions.hydroHeadM)} m drop, not enough to power the whole system`,
  ],
  [
    "Soil moisture",
    `${String(truth.siteAssumptions.moistureStartM3M3)} m³/m³ start; ${String(truth.siteAssumptions.moistureStopM3M3)} m³/m³ stop`,
  ],
];
const sourceBase = `${truth.source.repository}/blob/${truth.source.commit}/`;

export default function GroundTruthPage() {
  return (
    <main id="main" className={styles.reference}>
      <Link href="/">← NetLave home</Link>
      <Image
        src="/brand/logo-light.png"
        alt="NetLave logo"
        width={95}
        height={138}
      />
      <h1>NetLave ground truth</h1>
      <p>{truth.description}</p>
      <h2>What is NetLave?</h2>
      <p>{truth.authority}</p>
      <h2>Is it a real installation or a proven self-powered forest?</h2>
      <p>{truth.claimLimit}</p>
      <h2>What does the model assume?</h2>
      <p>
        All values below are synthetic assumptions or derived checks, not
        surveyed site data.
      </p>
      <dl>
        {facts.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <ul>
        {truth.zones.map((zone) => (
          <li key={zone.id}>
            Zone {zone.id}: {zone.areaHa} ha, {zone.feed.toLowerCase()}, +
            {zone.elevationM} m elevation, up to {zone.maxFlowM3Hour} m³/h.
          </li>
        ))}
      </ul>
      <h2>Which scenarios can be explored?</h2>
      {truth.scenarios.map((scenario) => (
        <section key={scenario.id}>
          <h3>{scenario.label}</h3>
          <p>{scenario.summary}</p>
        </section>
      ))}
      <h2>Does smart control save water?</h2>
      <p>{truth.evidence}</p>
      <div className={styles.tableScroll}>
        <table>
          <caption>
            Historical synthetic baseline · seed 7 · 14 simulated days
          </caption>
          <thead>
            <tr>
              <th scope="col">Metric</th>
              <th scope="col">Fixed timer</th>
              <th scope="col">Smart hysteresis</th>
            </tr>
          </thead>
          <tbody>
            {truth.comparison.map((metric) => (
              <tr key={metric.label}>
                <th scope="row">
                  {metric.label} ({metric.unit})
                </th>
                <td>{metric.fixed}</td>
                <td>{metric.smart}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h2>What is the status of resource-aware scheduling?</h2>
      <p>{truth.controllerStatus}</p>
      <h2>What are the safety and modelling limits?</h2>
      <p>{truth.safetyBoundary}</p>
      <p>{truth.modelLimit}</p>
      <h2>Who is behind NetLave?</h2>
      <p>
        The founder landing page identifies {truth.founders.join(", ")}. Roles
        and biographies have not been supplied; no contact email has been
        verified.
      </p>
      <p>
        <a href={truth.contactUrl}>Visit the project repository</a> to learn
        more and follow its development.
      </p>
      <h2>Sources and provenance</h2>
      <p>
        This same reference is published across the landing page, product
        website and digital twin. Physical authority remains in Python, not this
        static reference.
      </p>
      <ul>
        <li>
          <a href={`${sourceBase}${truth.source.parameters}`}>
            Synthetic parameters and assumptions
          </a>
        </li>
        <li>
          <a href={`${sourceBase}${truth.source.scenarios}`}>
            Scenario presets
          </a>
        </li>
        <li>
          <a href={`${sourceBase}${truth.source.reference}`}>
            Historical baseline comparison and model documentation
          </a>
        </li>
        <li>
          <a href={`${sourceBase}${truth.source.validation}`}>
            Held-out combined scheduler validation
          </a>
        </li>
        <li>
          <a href="https://www.fao.org/4/X0490E/x0490e0e.htm">
            FAO-56: readily available soil water
          </a>
        </li>
      </ul>
      <p>
        Reference source commit: <code>{truth.source.commit}</code>.
      </p>
    </main>
  );
}
