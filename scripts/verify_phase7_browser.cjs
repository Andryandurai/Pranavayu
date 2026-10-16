/* Live local QA; uses the retained database, never fetches new research data. */
const fs = require("fs");
const assert = require("assert");
const { chromium } = require("../.tools/ui-preview/node_modules/playwright");
const origin = "http://127.0.0.1:8000";

(async () => {
  const browser = await chromium.launch({
    channel: "msedge",
    headless: true,
    args: ["--enable-unsafe-swiftshader"],
  });
  const results = [];
  try {
    for (const width of [1440, 390]) {
      for (const route of [
        "dashboard",
        "overview",
        "forecasts",
        "research",
        "library",
        "ask",
        "vayusim",
      ]) {
        const page = await browser.newPage({
          viewport: { width, height: 1000 },
          deviceScaleFactor: 1,
        });
        const errors = [],
          external = new Set();
        page.on("pageerror", (error) => errors.push(error.message));
        page.on("request", (request) => {
          const url = new URL(request.url());
          if (url.protocol.startsWith("http") && url.hostname !== "127.0.0.1")
            external.add(url.hostname);
        });
        const path = route === "overview" ? "/" : "/" + route + "/";
        const response = await page.goto(origin + path, {
          waitUntil: "domcontentloaded",
          timeout: 45000,
        });
        assert.equal(response.status(), 200, path);
        if (route === "vayusim") {
          await page.waitForFunction(() => window.vayuState?.runId, {
            timeout: 45000,
          });
          assert.equal(
            await page.locator("#scene-validation").innerText(),
            "unvalidated branch",
          );
          assert.equal(
            await page.locator("#summary-validation").innerText(),
            "unvalidated branch",
          );
          assert.equal(
            await page.locator(".example-card .branch-label").count(),
            3,
          );
        }
        if (route === "dashboard") {
          assert.equal(await page.locator(".coverage-fail").count(), 14);
          assert.equal(
            await page.locator(".forecast-table .result-warning").count(),
            9,
          );
          assert(
            (
              await page.locator(".evidence-limits").first().innerText()
            ).includes("local LLM failed its quality gate"),
          );
          const links = await page
            .locator('a[href^="/evidence/"]')
            .evaluateAll((nodes) => [
              ...new Set(
                nodes.map((n) => n.getAttribute("href").split("#")[0]),
              ),
            ]);
          for (const link of links) {
            const r = await page.request.get(origin + link);
            assert.equal(r.status(), 200, link);
          }
          results.push({
            evidence_links: links.length,
            all_evidence_links_status: 200,
            width,
          });
          await page.screenshot({
            path: `docs/results/phase7-dashboard-${width}.png`,
          });
          await page.locator("#evidence-theme").click();
          assert.equal(
            await page
              .locator("#evidence-dashboard")
              .getAttribute("data-theme"),
            "dark",
          );
          await page.screenshot({
            path: `docs/results/phase7-dashboard-dark-${width}.png`,
          });
          assert.equal(
            await page.evaluate(
              () => document.documentElement.scrollWidth > innerWidth,
            ),
            false,
          );
          await page.locator("#assistant").scrollIntoViewIfNeeded();
          await page.screenshot({
            path: `docs/results/phase7-dashboard-assistant-${width}.png`,
          });
        }
        if (route === "ask")
          assert(
            (await page.locator(".page-heading").innerText()).includes(
              "has not passed the answer-quality gate",
            ),
          );
        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth > innerWidth,
        );
        assert.equal(overflow, false, path + " overflow");
        assert.deepEqual(errors, []);
        for (const host of external)
          assert.equal(host, "tile.openstreetmap.org");
        if (route !== "dashboard")
          await page.screenshot({
            path: `docs/results/phase7-${route}-${width}.png`,
          });
        const row = {
          route,
          width,
          status: response.status(),
          horizontal_overflow: overflow,
          js_errors: errors,
          external_hosts: [...external],
        };
        results.push(row);
        console.log(JSON.stringify(row));
        await page.close();
      }
    }
    // Execute both demo prompts in the actual extractive UI.
    const page = await browser.newPage({
      viewport: { width: 1440, height: 1000 },
    });
    const demos = [];
    for (const [kind, question] of [
      ["answer", "What was the annual mean PM2.5 in Delhi in 2025?"],
      ["refusal", "What was the annual mean PM2.5 in Delhi in 2020?"],
    ]) {
      await page.goto(origin + "/ask/");
      await page.locator("#question").fill(question);
      const previousAnswer = await page.locator("#answer").innerText();
      const responsePromise = page.waitForResponse(
        (r) => r.url() === origin + "/ask/" && r.request().method() === "POST",
        { timeout: 60000 },
      );
      await page.locator('button[type="submit"]').click();
      const response = await responsePromise;
      assert.equal(response.status(), 200);
      await page.waitForFunction((before) => {
        const text = document.querySelector("#answer").innerText.trim();
        return text.length > 20 && text !== before.trim();
      }, previousAnswer);
      const text = await page.locator("#answer").innerText();
      const citations = await page.locator('#answer a[href^="/api/"]').count();
      if (kind === "answer") assert(citations > 0, text);
      else
        assert(
          /insufficient evidence|unavailable|not available|missing|no .*data|cannot|do not have|not have|no .*observations/i.test(
            text,
          ),
          text,
        );
      await page.locator("#answer").scrollIntoViewIfNeeded();
      await page.screenshot({ path: `docs/results/phase7-demo-${kind}.png` });
      demos.push({
        kind,
        question,
        status: response.status(),
        citations,
        text,
      });
      console.log(
        JSON.stringify({
          kind,
          status: response.status(),
          citations,
          text: text.slice(0, 500),
        }),
      );
    }
    fs.writeFileSync(
      "data/results/phase7/demo-browser.json",
      JSON.stringify(demos, null, 2) + "\n",
    );
  } finally {
    await browser.close();
    fs.writeFileSync(
      "data/results/phase7/browser.json",
      JSON.stringify(results, null, 2) + "\n",
    );
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
