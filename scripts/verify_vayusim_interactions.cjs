const fs = require("fs"),
  assert = require("assert");
const { chromium } = require("../.tools/ui-preview/node_modules/playwright");
const base = "http://127.0.0.1:8000";
(async () => {
  for (let attempt = 0; attempt < 12; attempt++) {
    try {
      const r = await fetch(base + "/vayusim/?run=62", {
        signal: AbortSignal.timeout(10000),
      });
      if (r.ok) break;
    } catch {}
    if (attempt === 11) throw new Error("Web readiness timeout");
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  const browser = await chromium.launch({
    channel: "msedge",
    headless: true,
    args: ["--enable-unsafe-swiftshader"],
  });
  const records = {};
  try {
    const page = await browser.newPage({
      viewport: { width: 1440, height: 1080 },
    });
    const errors = [],
      external = new Set();
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("request", (r) => {
      const u = new URL(r.url());
      if (u.protocol.startsWith("http") && u.hostname !== "127.0.0.1")
        external.add(u.hostname);
    });
    await page.goto(base + "/vayusim/?run=62");
    await page.waitForFunction(() => window.vayuState?.runId === 62);
    console.log("Initial stored run and map loaded");
    // Stored second run, zero emissions; source and difference remain distinct controls.
    await page.locator("#view-baseline").click();
    await page.waitForFunction(() =>
      document
        .querySelector("#comparison-note")
        .textContent.includes("stored runs"),
    );
    assert((await page.locator("#peak").innerText()).startsWith("0"));
    const baselineId = await page.evaluate(() => window.vayuState.runId);
    assert.notEqual(baselineId, 62);
    await page.locator("#view-difference").click();
    await page.waitForFunction(
      () =>
        document
          .querySelector("#view-difference")
          .getAttribute("aria-pressed") === "true",
    );
    assert((await page.locator("#peak").innerText()).startsWith("15.64"));
    records.comparison = {
      source_run: 62,
      source_removed_run: baselineId,
      difference_label: await page.locator("#comparison-note").innerText(),
    };
    console.log("Stored comparison passed", JSON.stringify(records.comparison));
    // Stored supplementary grid and visible branch text.
    await page.locator("#section-button").click();
    await page.waitForFunction(
      () =>
        document
          .querySelector("#section-values")
          .textContent.includes("61 heights"),
      { timeout: 45000 },
    );
    records.section = await page.locator("#section-values").innerText();
    assert(records.section.includes("unvalidated branch"));
    console.log("Stored vertical grid passed");
    await page.screenshot({
      path: "docs/results/phase6b-cross-section.png",
      fullPage: true,
    });
    // Keyboard crosshair can place a source without a pointer.
    await page.locator("#vayu-map").focus();
    const original = await page.locator("#lon").inputValue();
    await page.keyboard.press("ArrowRight");
    await page.keyboard.press("Enter");
    assert.notEqual(await page.locator("#lon").inputValue(), original);
    records.keyboard_source = true;
    // Source fields remain stored for day; map-only edits need explicit Run.
    const dayStart = Date.now();
    await page.locator("#day-button").click();
    await page.waitForFunction(() => window.vayuDay?.available === 24, {
      timeout: 45000,
    });
    console.log("All 24 day fields cached");
    const prefetchMs = Date.now() - dayStart;
    let gridRequests = 0;
    const track = (r) => {
      if (/\/grid\/.*\.(bin|json|png)$/.test(new URL(r.url()).pathname))
        gridRequests++;
    };
    page.on("request", track);
    const frames = [];
    for (let hour = 0; hour < 24; hour++) {
      const start = Date.now();
      await page.locator("#timeline").evaluate((e, value) => {
        e.value = value;
        e.dispatchEvent(new Event("input", { bubbles: true }));
      }, hour);
      await page.waitForFunction(
        (h) =>
          document
            .querySelector("#timeline-label")
            .textContent.includes("T" + String(h).padStart(2, "0") + ":00"),
        hour,
      );
      await page.waitForFunction(
        () =>
          window.vayuState?.runId &&
          document
            .querySelector("#status")
            .textContent.startsWith("Stored hourly frame"),
      );
      frames.push(Date.now() - start);
      const v = await page.evaluate(() => window.vayuState.validationStatus);
      assert.equal(
        await page.locator("#scene-validation").innerText(),
        v === "unvalidated_branch"
          ? "unvalidated branch"
          : "formula check only",
      );
    }
    page.off("request", track);
    assert.equal(gridRequests, 0);
    await page.locator("#timeline").focus();
    await page.keyboard.press("Home");
    await page.keyboard.press("ArrowRight");
    assert.equal(await page.locator("#timeline").inputValue(), "1");
    await page.locator("#play-button").click();
    await page.waitForFunction(
      () => Number(document.querySelector("#timeline").value) > 1,
      { timeout: 5000 },
    );
    await page.locator("#play-button").click();
    records.day = {
      prefetch_seconds: prefetchMs / 1000,
      available: 24,
      cached_scrub_grid_requests: gridRequests,
      frame_selection_ms: frames,
      keyboard_timeline: true,
      playback: true,
      renderer: await page.evaluate(() => window.vayuState),
    };
    await page.screenshot({
      path: "docs/results/phase6b-day.png",
      fullPage: true,
    });
    await page.locator("#theme-toggle").click();
    assert.equal(
      await page.locator("#vayu").getAttribute("data-theme"),
      "light",
    );
    await page.screenshot({
      path: "docs/results/phase6b-light.png",
      fullPage: true,
    });
    records.light_mode = true;
    // Each actual shared slug opens with its status before JS hydration.
    records.shared = [];
    for (const id of [62, 63, 64]) {
      const run = await (
        await page.request.get(base + "/api/vayusim/runs/" + id + "/")
      ).json();
      await page.goto(base + "/vayusim/?scenario=" + run.scenario_slug);
      assert.equal(
        await page.locator("#scene-validation").innerText(),
        "unvalidated branch",
      );
      await page.waitForFunction(() => window.vayuState?.runId);
      records.shared.push({
        run_id: id,
        label: await page.locator("#summary-validation").innerText(),
      });
    }
    // Forced WebGL failure must still show a real PNG and all labels.
    const fallback = await browser.newPage({
      viewport: { width: 390, height: 1000 },
    });
    await fallback.addInitScript(() => {
      const original = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function (type, ...args) {
        return type.startsWith("webgl")
          ? null
          : original.call(this, type, ...args);
      };
    });
    await fallback.goto(base + "/vayusim/?run=64");
    await fallback.waitForFunction(() => window.vayuState?.runId === 64);
    assert(await fallback.locator("#fallback-map").isVisible());
    assert.equal(
      await fallback.locator("#scene-validation").innerText(),
      "unvalidated branch",
    );
    await fallback.waitForFunction(() => {
      const i = document.querySelector("#fallback-image");
      return i.complete && i.naturalWidth > 0;
    });
    await fallback.screenshot({
      path: "docs/results/phase6b-fallback-phone.png",
      fullPage: true,
    });
    records.fallback = true;
    // Initial request budgets refer to actual local rendering, not tile/network latency.
    for (const host of external) assert.equal(host, "tile.openstreetmap.org");
    assert.deepEqual(errors, []);
    records.external_hosts = [...external];
    records.js_errors = errors;
  } finally {
    await browser.close();
    fs.writeFileSync(
      "data/results/phase6b/interactions.json",
      JSON.stringify(records, null, 2) + "\n",
    );
  }
  console.log(JSON.stringify(records, null, 2));
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
