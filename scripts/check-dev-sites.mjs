import assert from "node:assert/strict";
import { chromium } from "@playwright/test";

// Run after starting the three pnpm dev servers on 3000 / 3001 / 3002.
const browser = await chromium.launch();
try {
  for (const [name, port] of [
    ["landing", 3000],
    ["product", 3001],
    ["twin", 3002],
  ]) {
    const page = await browser.newPage({
      viewport: { width: 1440, height: 900 },
    });
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (
        message.type() === "error" ||
        /THREE\.(Clock|WebGLShadowMap)/.test(message.text())
      )
        errors.push(message.text());
    });
    await page.goto(`http://localhost:${port}/`);
    await page
      .getByRole("heading", { name: "NetLave: the shared project facts" })
      .waitFor();
    if (name === "twin")
      await page.getByText("Live backend", { exact: true }).waitFor();
    await page.evaluate(async () => {
      for (
        let position = 0;
        position < document.body.scrollHeight;
        position += 600
      ) {
        window.scrollTo(0, position);
        await new Promise((resolve) => setTimeout(resolve, 150));
      }
      window.scrollTo(0, 0);
    });
    await page.waitForTimeout(1200);
    if (name === "product") {
      for (const selector of [
        'main a[href="#twin"]',
        '[aria-label="Explore connected systems"] button',
        '[aria-label="Choose a scenario preview"] button',
      ]) {
        const control = page.locator(selector).first();
        assert.equal(
          await control.evaluate(
            (element) => getComputedStyle(element).borderRadius,
          ),
          "999px",
        );
      }
      await page.getByRole("button", { name: /Recover the energy/ }).click();
      await page
        .getByRole("heading", { name: "Renewable power. Physical limits." })
        .waitFor();
      await page.getByRole("button", { name: /Low solar/ }).click();
      await page
        .getByRole("heading", { name: "Protect the battery. Pause the pump." })
        .waitFor();
    }
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      `${name}: mobile overflow`,
    );
    if (name === "product") {
      await page.getByRole("button", { name: "Menu +", exact: true }).click();
      await page.getByRole("navigation", { name: "Mobile" }).waitFor();
    }
    assert.deepEqual(errors, [], `${name}: dev console must be clean`);
    await page.close();
    const noWebGl = await browser.newContext();
    await noWebGl.addInitScript(() => {
      const originalGetContext = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function (
        kind,
        ...argumentsList
      ) {
        if (
          kind === "webgl" ||
          kind === "webgl2" ||
          kind === "experimental-webgl"
        )
          return null;
        return originalGetContext.call(this, kind, ...argumentsList);
      };
    });
    const fallback = await noWebGl.newPage();
    const fallbackErrors = [];
    fallback.on("pageerror", (error) => fallbackErrors.push(error.message));
    fallback.on("console", (message) => {
      if (message.type() === "error") fallbackErrors.push(message.text());
    });
    await fallback.goto(`http://localhost:${port}/`);
    await fallback
      .getByRole("heading", { name: "NetLave: the shared project facts" })
      .waitFor();
    await fallback.waitForTimeout(1200);
    assert.deepEqual(
      fallbackErrors,
      [],
      `${name}: no-WebGL fallback must remain usable`,
    );
    await noWebGl.close();
    console.log(
      `${name}: clean dev console, mobile layout, controls and no-WebGL fallback passed`,
    );
  }
} finally {
  await browser.close();
}
