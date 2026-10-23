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

test("matched experiment shows the candidate and scored window without changing the live clock", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByText("Live backend", { exact: true })).toBeVisible();
  await page
    .getByRole("combobox", { name: "Scenario", exact: true })
    .selectOption("tse_interrupt");
  await page
    .getByRole("combobox", { name: "Control", exact: true })
    .selectOption("SMART_HYSTERESIS");
  await page.getByRole("button", { name: "Load run", exact: true }).click();
  await expect(page.getByText(/Step 0 · 60 s per step/)).toBeVisible();
  await page
    .getByRole("checkbox", { name: "Matched operation (10-day warm-up)" })
    .check();
  await page
    .getByRole("checkbox", { name: "Include experimental scheduler" })
    .check();
  await page.getByRole("spinbutton", { name: "Days", exact: true }).fill("1");
  await page.getByRole("button", { name: "Run A/B", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Experimental scheduler service" }),
  ).toBeVisible();
  await expect(
    page.getByText(/MATCHED_OPERATION · warm-up 10 days/),
  ).toBeVisible();
  await expect(page.getByText(/measured steps \[14400, 15840\)/)).toBeVisible();
  await expect(page.getByText(/Step 0 · 60 s per step/)).toBeVisible();
});
