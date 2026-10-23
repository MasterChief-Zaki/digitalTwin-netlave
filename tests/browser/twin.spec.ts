import { expect, test } from "@playwright/test";
import type { SimulationSnapshot } from "../../src/types/simulation";

// Assert actual scene transforms, not just overlay text, against real Python replies.
test("schematic tracks snapshots and selection in both directions", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (/THREE\.(Clock|WebGLShadowMap)/.test(message.text())) {
      errors.push(message.text());
    }
  });
  await page.goto("/");
  await expect(page.getByText("Live backend", { exact: true })).toBeVisible();
  const canvas = page
    .getByLabel("Live schematic forest digital twin")
    .locator("canvas");
  await expect(canvas).toHaveAttribute("data-rendered-step", /\d+/);
  for (const zone of ["a", "b", "c"]) {
    await expect(canvas).toHaveAttribute(`data-zone-${zone}-tree-count`, "40");
    await expect
      .poll(async () =>
        Number(await canvas.getAttribute(`data-zone-${zone}-tree-spread`)),
      )
      .toBeGreaterThan(6);
  }
  await page
    .getByRole("combobox", { name: "Scenario", exact: true })
    .selectOption("baseline");
  await page
    .getByRole("combobox", { name: "Control", exact: true })
    .selectOption("SMART_HYSTERESIS");
  const resetReply = page.waitForResponse(
    (response) => response.url().endsWith("/api/reset") && response.ok(),
  );
  await page.getByRole("button", { name: "Load run", exact: true }).click();
  const initial = (await (await resetReply).json()) as SimulationSnapshot;
  await expect(canvas).toHaveAttribute(
    "data-rendered-generation",
    String(initial.run_generation),
  );
  await expect
    .poll(async () =>
      Number(await canvas.getAttribute("data-water-elevation-y")),
    )
    .toBeCloseTo(initial.reservoir.surface_elevation_m * 0.16, 3);
  await expect(canvas).toHaveAttribute("data-water-visible", "true");
  await expect
    .poll(async () => Number(await canvas.getAttribute("data-water-depth")))
    .toBeCloseTo(
      (initial.reservoir.surface_elevation_m -
        initial.reservoir.floor_elevation_m) *
        0.16,
      3,
    );

  // Select B by clicking its projected terrace center in the actual WebGL canvas.
  await canvas.scrollIntoViewIfNeeded();
  const box = await canvas.boundingBox();
  if (!box) throw new Error("Canvas must have a visible bounding box");
  const horizontal = Number(await canvas.getAttribute("data-zone-b-screen-x"));
  const vertical = Number(await canvas.getAttribute("data-zone-b-screen-y"));
  await page.mouse.click(box.x + horizontal, box.y + vertical);
  await expect(canvas).toHaveAttribute("data-selected-zone", "B");
  await expect(
    page.getByRole("button", { name: /^Zone B gravity/ }),
  ).toHaveAttribute("aria-pressed", "true");
  await page
    .getByRole("group", { name: "Schematic zone selection" })
    .getByRole("button", { name: "Zone A", exact: true })
    .click();
  await expect(canvas).toHaveAttribute("data-selected-zone", "A");

  const advanceReply = page.waitForResponse(
    (response) => response.url().endsWith("/api/advance") && response.ok(),
  );
  await page.getByRole("button", { name: "+1 min", exact: true }).click();
  const advanced = (await (await advanceReply).json()) as {
    snapshot: SimulationSnapshot;
  };
  await expect(canvas).toHaveAttribute(
    "data-rendered-step",
    String(advanced.snapshot.step),
  );
  await expect(canvas).toHaveAttribute("data-zone-a-state", "active");
  await expect(canvas).toHaveAttribute("data-zone-b-state", "waiting");
  await expect
    .poll(async () => Number(await canvas.getAttribute("data-battery-fill")))
    .toBeCloseTo(advanced.snapshot.energy.battery_soc_0_1 * 1.4, 2);

  await page
    .getByRole("combobox", { name: "Control", exact: true })
    .selectOption("SMART_RESOURCE_AWARE");
  await page.getByRole("button", { name: "Load run", exact: true }).click();
  await page.getByRole("button", { name: "+1 min", exact: true }).click();
  await expect(canvas).toHaveAttribute("data-zone-a-state", "waiting");
  // Pump reserve denial must stop the actual water-direction marker, not just its label.
  await page
    .getByRole("combobox", { name: "Scenario", exact: true })
    .selectOption("low_solar");
  await page
    .getByRole("combobox", { name: "Control", exact: true })
    .selectOption("SMART_HYSTERESIS");
  await page.getByRole("button", { name: "Load run", exact: true }).click();
  await page.getByRole("button", { name: "+1 h", exact: true }).click();
  await expect(canvas).toHaveAttribute("data-zone-c-state", "fault");
  await expect(canvas).toHaveAttribute("data-pumped-water-moving", "false");
  await expect(canvas).toHaveAttribute("data-inlet-moving", "true");
  // Cutting the inlet must stop its rendered flow too.
  await page.getByRole("button", { name: /Cut TSE inflow/ }).click();
  await page.getByRole("button", { name: "+1 min", exact: true }).click();
  await expect(canvas).toHaveAttribute("data-inlet-moving", "false");
  await page.setViewportSize({ width: 900, height: 900 });
  for (const zone of ["a", "b", "c"]) {
    await expect(canvas).toHaveAttribute(`data-zone-${zone}-tree-count`, "40");
    await expect
      .poll(async () =>
        Number(await canvas.getAttribute(`data-zone-${zone}-tree-spread`)),
      )
      .toBeGreaterThan(6);
  }
  await page.reload();
  await expect(canvas).toHaveAttribute("data-zone-a-tree-count", "40");
  await expect
    .poll(async () =>
      Number(await canvas.getAttribute("data-zone-a-tree-spread")),
    )
    .toBeGreaterThan(6);
  expect(errors).toEqual([]);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.setViewportSize({ width: 900, height: 900 });
  await page
    .getByLabel("Schematic snapshot status")
    .screenshot({ path: "test-results/schematic-readout.png" });
  await canvas.screenshot({ path: "test-results/schematic-canvas.png" });
});
