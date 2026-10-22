// Joins the CSS-module classes that apply. Module lookups are typed
// `string | undefined`, and conditions may yield `false`; both are skipped.
export function classNames(
  ...candidates: (string | false | null | undefined)[]
): string {
  return candidates.filter(Boolean).join(" ");
}
