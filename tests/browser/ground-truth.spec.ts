import { expect, test } from "@playwright/test";
import truth from "../../src/content/ground-truth.json";

test("shared reference is crawlable, branded and clear about claim limits", async ({
  page,
  request,
}) => {
  const response = await request.get("/ground-truth");
  expect(response.ok()).toBeTruthy();
  const html = await response.text();
  expect(html).toContain(truth.claimLimit);
  expect(html).toContain(truth.source.commit);
  expect(html).toContain("application/ld+json");
  expect(html).toContain("og:title");
  expect(html).toContain("twitter:card");
  expect(html).toContain("apple-touch-icon");
  expect(html).toContain(
    'rel="canonical" href="http://127.0.0.1:3100/ground-truth"',
  );
  expect(html).toContain("http://127.0.0.1:3100/brand/social.png");
  const sitemap = await (await request.get("/sitemap.xml")).text();
  expect(sitemap).toContain("http://127.0.0.1:3100/ground-truth");
  expect(sitemap).not.toContain("example.com");
  await page.goto("/");
  await expect(
    page.getByRole("link", { name: "NetLave home", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: /Read the assumptions/ }).click();
  await expect(
    page.getByRole("heading", { name: "NetLave ground truth", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("main").getByText(truth.controllerStatus, { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("table")).toBeVisible();
  await expect(
    page.getByRole("link", {
      name: "Visit the project repository",
      exact: true,
    }),
  ).toHaveAttribute(
    "href",
    "https://github.com/MasterChief-Zaki/landing-netlave",
  );
  const schema = JSON.parse(
    await page
      .locator('script[type="application/ld+json"]')
      .first()
      .innerHTML(),
  ) as { name: string; "@type": string };
  expect(schema.name).toBe("NetLave");
  expect(schema["@type"]).toBe("WebSite");
  expect((await request.get("/favicon.ico")).ok()).toBeTruthy();
  expect((await request.get("/brand/social.png")).ok()).toBeTruthy();
  expect(await (await request.get("/llms.txt")).text()).toContain(
    "not a real-site calibrated installation",
  );
  expect(await (await request.get("/robots.txt")).text()).toContain(
    "Disallow: /api/",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});
