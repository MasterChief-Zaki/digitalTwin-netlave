import { expect, test } from "@playwright/test";

test("dashboard and schematic selection remain usable without WebGL", async ({
  page,
}) => {
  await page.addInitScript(() => {
    // Simulate a browser with no canvas rendering contexts; all readings remain DOM.
    Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
      configurable: true,
      value: () => null,
    });
  });
  await page.goto("/");
  await expect(page.getByText(/The 3D site view needs WebGL/)).toBeVisible();
  await expect(page.getByText("Live backend", { exact: true })).toBeVisible();
  await page
    .getByRole("group", { name: "Schematic zone selection" })
    .getByRole("button", { name: "Zone B", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: /^Zone B gravity/ }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.getByRole("button", { name: "+1 min", exact: true }),
  ).toBeEnabled();
});
