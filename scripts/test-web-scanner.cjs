// Run against an isolated built preview: CARDYSSEY_TEST_URL=http://127.0.0.1:3011
// Requires Playwright (NODE_PATH may point to a temporary installation).
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
(async () => {
  const base = process.env.CARDYSSEY_TEST_URL || "http://127.0.0.1:3011";
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox", "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"] });
  try {
    const context = await browser.newContext({ permissions: ["camera"] });
    await context.addCookies([{ name: "cardyssey_access", value: "local-test-only", url: base }]);
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.route("**/api/**", route => {
      const url = route.request().url();
      if (url.includes("/auth/me") || url.endsWith("/me")) return route.fulfill({json:{id:"test",email:"local@example.invalid",friendCode:"TEST"}});
      return route.fulfill({json:{}});
    });
    const response = await page.goto(base + "/scan");
    assert.equal(response.status(), 200);
    assert.match(response.headers()["content-security-policy"], /worker-src 'self' blob:/);
    assert.match(response.headers()["content-security-policy"], /wasm-unsafe-eval/);
    await page.getByRole("button", { name: "Kamera starten", exact: true }).click();
    await page.waitForFunction(() => {
      const video = document.querySelector("video");
      return video && video.srcObject && video.readyState >= 2 && video.videoWidth > 0;
    });
    await page.evaluate(() => { window.testStream = document.querySelector("video").srcObject; });
    await page.getByRole("button", { name: "Foto aufnehmen", exact: true }).click();
    assert.ok(await page.locator('img[alt="Aufgenommene Karte"]').count());
    assert.ok(await page.evaluate(() => window.testStream.getTracks().every(track => track.readyState === "ended")));
    await page.getByRole("button", { name: "Neu aufnehmen", exact: true }).click();
    await page.getByRole("button", { name: "Kamera starten", exact: true }).click();
    await page.waitForFunction(() => document.querySelector("video")?.videoWidth > 0);
    await page.evaluate(() => { window.secondStream = document.querySelector("video").srcObject; });
    // Client navigation must release the camera on unmount.
    await page.getByRole("link", { name: "Account", exact: true }).first().click();
    await page.waitForFunction(() => window.secondStream.getTracks().every(track => track.readyState === "ended"));
    assert.equal(errors.length, 0, errors.join("\n"));
    const worker = await context.request.get(base + "/vendor/tesseract/worker.min.js");
    assert.equal(worker.status(),200);
    const core = await context.request.get(base + "/vendor/tesseract/tesseract-core-lstm.wasm.js");
    assert.equal(core.status(),200);
    console.log("PASS: preview stream, capture, track cleanup, restart, unmount and OCR CSP/assets");
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
