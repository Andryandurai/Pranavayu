(() => {
  const $ = (id) => document.getElementById(id),
    num = (v, d = 1) =>
      v == null
        ? "Unavailable"
        : Number(v).toLocaleString("en-IN", { maximumFractionDigits: d });
  const node = (tag, text, parent, cls) => {
    const e = document.createElement(tag);
    e.textContent = text;
    if (cls) e.className = cls;
    if (parent) parent.append(e);
    return e;
  };
  let requestNumber = 0;
  function chart(rows, parent) {
    const valid = rows.filter((r) => Number.isFinite(r.mean));
    if (!valid.length) return;
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 520 170");
    svg.setAttribute("role", "img");
    const title = document.createElementNS(ns, "title");
    title.textContent =
      "Observed annual PM2.5 means. Calendar spacing retains the unobserved2020–2023 gap.";
    svg.append(title);
    const max = Math.max(...valid.map((r) => r.mean));
    for (const row of valid) {
      const x = 30 + (row.year - 2015) * 44,
        y = 132 - (row.mean / max) * 95;
      const rect = document.createElementNS(ns, "rect");
      for (const [k, v] of Object.entries({
        x,
        y,
        width: 22,
        height: 132 - y,
        rx: 3,
        fill: row.year >= 2024 ? "#0b6557" : "#a4c4a0",
      }))
        rect.setAttribute(k, v);
      const label = document.createElementNS(ns, "title");
      label.textContent =
        row.year +
        ": " +
        num(row.mean) +
        " µg/m³; " +
        row.valid_days +
        " valid days";
      rect.append(label);
      svg.append(rect);
      const text = document.createElementNS(ns, "text");
      text.setAttribute("x", x - 2);
      text.setAttribute("y", 152);
      text.setAttribute("font-size", 10);
      text.setAttribute("fill", "#607269");
      text.textContent = row.year;
      svg.append(text);
    }
    const wrap = node("div", "", parent, "chart-wrap");
    wrap.append(svg);
    node(
      "p",
      "Observed annual means (µg/m³) · absent years remain blank",
      parent,
      "help",
    );
  }
  async function load() {
    const request = ++requestNumber;
    const kind = $("research-kind").value,
      network = $("research-cohort").value;
    $("research-status").textContent = "Loading recorded comparisons…";
    $("research-results").replaceChildren();
    try {
      const response = await fetch("/api/analytics/" + kind + "/");
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Research unavailable");
      if (request !== requestNumber) return;
      $("research-status").textContent =
        data.label + " · stored Run " + data.run;
      for (const record of data.results) {
        const result = record.result,
          cohort = result.cohorts?.[network];
        const card = node("article", "", $("research-results"), "panel");
        const top = node("div", "", card, "card-top");
        node(
          "h2",
          record.city__slug[0].toUpperCase() + record.city__slug.slice(1),
          top,
        );
        node(
          "span",
          network === "fixed_panel" ? "Fixed panel" : "All stations",
          top,
          "badge",
        );
        if (!cohort) {
          node("p", "This station cohort is unavailable.", card);
          continue;
        }
        node("p", cohort.scope || "Descriptive evidence", card, "help");
        chart(cohort.annual || [], card);
        const comparison =
          kind === "ncap" ? cohort.comparison : cohort.long_run_comparison;
        if (!comparison?.raw) {
          node(
            "p",
            comparison?.reason ||
              "This period comparison is unavailable; eligibility or model readiness requirements were not met.",
            card,
          );
          continue;
        }
        node(
          "p",
          "Baseline: " +
            comparison.baseline_years?.join(", ") +
            " · recent: " +
            comparison.recent_years?.join(", "),
          card,
          "help",
        );
        for (const [key, label] of [
          ["raw", "Observed difference"],
          ["normalised", "Normalised difference"],
        ]) {
          const v = comparison[key];
          if (!v) continue;
          node("h3", label, card);
          node(
            "p",
            num(v.difference, 2) + " µg/m³ (" + num(v.percent_change, 1) + "%)",
            card,
          );
          node(
            "p",
            "95% interval: " +
              v.ci95_difference.map((x) => num(x, 2)).join(" to ") +
              " µg/m³",
            card,
            "help",
          );
        }
        node(
          "p",
          comparison.uncertainty ||
            "Read the reported bootstrap interval with the observed network and period limitations.",
          card,
          "help",
        );
        const url = "/api/analytics/" + kind + "/";
        const a = node("a", "Inspect the stored evidence →", card, "text-link");
        a.href = url;
      }
    } catch (error) {
      if (request === requestNumber)
        $("research-status").textContent = error.message;
    }
  }
  $("research-kind").addEventListener("change", load);
  $("research-cohort").addEventListener("change", load);
  load();
})();
