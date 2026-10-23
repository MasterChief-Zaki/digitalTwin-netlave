import { expect, test } from "@playwright/test";

// Real FastAPI + production Next.js: no mocked service metrics.
test("low-solar service failure remains visible beside admitted-load autonomy", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByText("Live backend", { exact: true })).toBeVisible();
  await page
    .getByRole("combobox", { name: "Scenario", exact: true })
    .selectOption("low_solar");
  await page.getByRole("button", { name: "Load run", exact: true }).click();
  await page.getByRole("button", { name: "+1 day", exact: true }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Zone C service failure" }),
  ).toBeVisible();
  await expect(
    page.getByText("Electrical autonomy — admitted loads", { exact: true }),
  ).toBeVisible();
  await page.getByRole("spinbutton", { name: "Days", exact: true }).fill("1");
  await page.getByRole("button", { name: "Run A/B", exact: true }).click();
  await expect(
    page.getByText(/Identical input series and initial state/),
  ).toBeVisible();
  await expect(
    page.getByText(/this single-seed run is not validated/),
  ).toBeVisible();
});

test("resource-aware controller is explicitly experimental and opt-in", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByText("Live backend", { exact: true })).toBeVisible();
  await page
    .getByRole("combobox", { name: "Control", exact: true })
    .selectOption("SMART_RESOURCE_AWARE");
  await page.getByRole("button", { name: "Load run", exact: true }).click();
  await expect(
    page.getByRole("combobox", { name: "Control", exact: true }),
  ).toHaveValue("SMART_RESOURCE_AWARE");
  await page.getByRole("button", { name: "+1 h", exact: true }).click();
  await expect(page.getByText(/Scheduling deferral/).first()).toBeVisible();
});
