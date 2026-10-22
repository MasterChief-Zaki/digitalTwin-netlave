import { Color } from "three";

// Every color the scene uses, read once from the CSS tokens so the scene
// follows the design system instead of repeating hex values.
export interface TwinPalette {
  background: Color;
  surface: Color;
  border: Color;
  terrace: Color;
  metal: Color;
  water: Color;
  zoneA: Color;
  zoneB: Color;
  zoneC: Color;
  solar: Color;
  hydro: Color;
  active: Color;
  idle: Color;
  warning: Color;
  fault: Color;
  healthyCanopy: Color;
  dryCanopy: Color;
  trunk: Color;
  accent: Color;
}

function readToken(name: string): Color {
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return new Color(value);
}

export function readPalette(): TwinPalette {
  return {
    background: readToken("--color-background"),
    surface: readToken("--color-surface"),
    border: readToken("--color-border"),
    terrace: readToken("--color-deep-teal"),
    metal: readToken("--color-sage"),
    water: readToken("--color-series-zone-a"),
    zoneA: readToken("--color-series-zone-a"),
    zoneB: readToken("--color-series-zone-b"),
    zoneC: readToken("--color-series-zone-c"),
    solar: readToken("--color-series-solar"),
    hydro: readToken("--color-series-hydro"),
    active: readToken("--color-status-active"),
    idle: readToken("--color-status-idle"),
    warning: readToken("--color-status-warning"),
    fault: readToken("--color-status-fault"),
    healthyCanopy: readToken("--color-series-zone-c"),
    dryCanopy: readToken("--color-sand"),
    trunk: readToken("--color-lagoon"),
    accent: readToken("--color-accent"),
  };
}
