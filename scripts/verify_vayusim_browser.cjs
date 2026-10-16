const fs = require("fs");
const assert = require("assert");
const { chromium } = require("../.tools/ui-preview/node_modules/playwright");

(async () => {
  const browser = await chromium.launch({
    channel: "msedge",
    headless: true,
    args: ["--enable-unsafe-swiftshader"],
  });
  const records = [];
  try {
    for (const width of [1440, 390]) {
      for (const [city, id] of [
        ["delhi", 62],
        ["mumbai", 63],
        ["hyderabad", 64],
      ]) {
        const page = await browser.newPage({
          viewport: { width, height: 1080 },
          deviceScaleFactor: 1,
        });
        const errors = [],
          external = new Set();
        page.on("pageerror", (e) => errors.push(e.message));
        page.on("request", (r) => {
          const u = new URL(r.url());
          if (u.protocol.startsWith("http") && u.hostname !== "127.0.0.1")
            external.add(u.hostname);
        });
        const start = Date.now();
        const response = await page.goto(
          "http://127.0.0.1:8000/vayusim/?run=" + id,
          { waitUntil: "domcontentloaded", timeout: 45000 },
        );
        assert.equal(response.status(), 200);
        await page.waitForFunction(() => window.vayuState?.runId, {
          timeout: 45000,
        });
        for (const selector of [
          "#scene-validation",
          "#summary-validation",
          "#day-validation",
        ])
          assert.equal(
            await page.locator(selector).innerText(),
            "unvalidated branch",
          );
        assert.equal(await page.locator(".example-card").count(), 3);
        assert.equal(
          await page
            .locator(".example-card .branch-label")
            .allTextContents()
            .then((a) => a.every((v) => v === "unvalidated branch")),
          true,
        );
        assert.equal(
          await page.evaluate(
            () => document.documentElement.scrollWidth > window.innerWidth,
          ),
          false,
        );
        const webgl = await page.locator("#vayu-map").isVisible();
        assert.equal(
          webgl,
          true,
          "Normal browser must use the map and particle path",
        );
        const status = await page.locator("#status").innerText();
        await page.screenshot({
          path: `docs/results/phase6b-${city}-${width}.png`,
          fullPage: true,
        });
        const shared = await page.locator("#share-link").getAttribute("href");
        const exported = await page.request.get(
          "http://127.0.0.1:8000" +
            (await page.locator("#export-link").getAttribute("href")),
        );
        assert.equal(exported.status(), 200);
        assert.equal(
          exported.headers()["x-validation-status"],
          "unvalidated_branch",
        );
        if (width === 1440)
          fs.writeFileSync(
            `data/results/phase6b/export-${city}.png`,
            await exported.body(),
          );
        const frame = await page.evaluate(() => window.vayuState);
        for (const host of external)
          assert.equal(host, "tile.openstreetmap.org");
        assert.deepEqual(errors, []);
        records.push({
          city,
          width,
          http_status: response.status(),
          webgl,
          load_seconds: (Date.now() - start) / 1000,
          status,
          labels_visible: true,
          horizontal_overflow: false,
          external_hosts: [...external],
          js_errors: errors,
          shared_url: shared,
          export_status: exported.status(),
          frame,
        });
        console.log(
          JSON.stringify({
            ...records.at(-1),
            frame: { ...frame, renderTimes: frame.renderTimes.slice(0, 3) },
          }),
        );
        await page.close();
      }
    }
  } finally {
    await browser.close();
    fs.writeFileSync(
      "data/results/phase6b/browser.json",
      JSON.stringify(records, null, 2) + "\n",
    );
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
