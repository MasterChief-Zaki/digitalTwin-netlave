import { expect, test } from "@playwright/test";
import { initialSnapshot } from "../../src/fixtures/initialSnapshot";

test("old backend cannot replace compatible reservoir geometry", async ({
  page,
}) => {
  await page.route("**/api/state", async (route) => {
    const oldReservoir = Object.fromEntries(
      Object.entries(initialSnapshot.reservoir).filter(
        ([key]) => key !== "floor_elevation_m" && key !== "depth_at_capacity_m",
      ),
    );
    await route.fulfill({
      json: {
        ...initialSnapshot,
        schema_version: "1.1",
        reservoir: oldReservoir,
      },
    });
  });
  await page.goto("/");
  await expect(
    page.getByRole("status").filter({ hasText: "backend is out of date" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Play", exact: true }),
  ).toBeDisabled();
  const canvas = page
    .getByLabel("Live schematic forest digital twin")
    .locator("canvas");
  await expect(canvas).toHaveAttribute("data-water-elevation-y", "3.52");
  await expect(canvas).toHaveAttribute("data-water-visible", "true");
});

test("invalid reservoir geometry is rejected before rendering", async ({
  page,
}) => {
  await page.route("**/api/state", async (route) => {
    await route.fulfill({
      json: {
        ...initialSnapshot,
        reservoir: { ...initialSnapshot.reservoir, floor_elevation_m: null },
      },
    });
  });
  await page.goto("/");
  await expect(
    page
      .getByRole("status")
      .filter({ hasText: "invalid reservoir floor_elevation_m" }),
  ).toBeVisible();
  const canvas = page
    .getByLabel("Live schematic forest digital twin")
    .locator("canvas");
  await expect(canvas).toHaveAttribute("data-water-elevation-y", "3.52");
});
