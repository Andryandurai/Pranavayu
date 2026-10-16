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
  const city = $("forecast-city");
  const requested = new URLSearchParams(location.search).get("city");
  if ([...city.options].some((o) => o.value === requested))
    city.value = requested;
  let activeRequest = 0;
  async function load() {
    const request = ++activeRequest;
    const slug = city.value;
    $("forecast-status").textContent = "Loading stored forecasts…";
    $("forecast-cards").replaceChildren();
    $("forecast-evaluation").replaceChildren();
    try {
      const [latest, evaluation] = await Promise.all(
        [
          "/api/forecast/" + slug + "/latest/",
          "/api/forecast/" + slug + "/evaluation/",
        ].map(async (url) => {
          const response = await fetch(url);
          const data = await response.json();
          if (!response.ok)
            throw new Error(data.detail || "Forecast unavailable");
          return data;
        }),
      );
      if (request !== activeRequest) return;
      const issued = latest.forecasts[0];
      $("forecast-status").textContent =
        "Issued for " +
        issued.issued_for_date +
        " IST · " +
        issued.mode +
        " · stored Run " +
        latest.run;
      for (const row of latest.forecasts) {
        const card = node(
          "article",
          "",
          $("forecast-cards"),
          "panel forecast-card",
        );
        const top = node("div", "", card, "card-top");
        node("h2", "Day +" + row.horizon, top);
        node("span", row.mode, top, "badge warning");
        node("p", row.target_date + " · daily PM2.5", card, "help");
        node("p", "forecast_method: " + row.forecast_method, card, "forecast-method");
        node(
          "p",
          "policy_source: " + row.policy_source +
            (row.fallback_used ? " · fallback: " + row.fallback_reason : " · fallback: no"),
          card,
          "help",
        );
        const value = node("p", num(row.point), card, "city-value");
        node("span", "µg/m³", value);
        node(
          "p",
          row.aqi_category.replaceAll("_", " ") + " · PM2.5 subindex category",
          card,
          "help",
        );
        node("div", "", card, "range-bar");
        node(
          "p",
          "80% interval: " +
            (row.lower80 == null || row.upper80 == null
              ? "unavailable for persistence override"
              : num(row.lower80) + "–" + num(row.upper80) + " µg/m³"),
          card,
        );
        node(
          "p",
          "95% interval: " +
            (row.lower95 == null || row.upper95 == null
              ? "unavailable for persistence override"
              : num(row.lower95) + "–" + num(row.upper95) + " µg/m³"),
          card,
          "help",
        );
        if (
          row.lower80 != null && row.upper80 != null &&
          (row.point < row.lower80 || row.point > row.upper80)
        )
          node(
            "p",
            "The chosen target interval excludes this separate point forecast.",
            card,
            "help",
          );
        const choices = row.interval_policy?.choices || {};
        if (row.interval_policy?.serving_note)
          node("p", row.interval_policy.serving_note, card, "help");
        for (const [level, policy] of Object.entries(choices)) {
          node(
            "p",
            level +
              "%: " +
              policy.method.replaceAll("_", " ") +
              " · empirical coverage " +
              num(policy.coverage * 100) +
              "%",
            card,
            "help",
          );
          if (!policy.coverage_gate_passed)
            node(
              "p",
              "Coverage rule failed: " +
                (policy.warning || "No available method meets the rule."),
              card,
              "help",
            );
        }
        node("h3", "Conditional drivers", card);
        for (const driver of row.top_drivers || [])
          node(
            "p",
            typeof driver === "object"
              ? (driver.feature || driver.name || "Driver") +
                  ": " +
                  num(driver.shap_value ?? driver.shap, 2) +
                  " µg/m³ contribution"
              : String(driver),
            card,
            "help",
          );
        node(
          "p",
          "Model " +
            row.model_version +
            " · " +
            row.algorithm +
            " · " +
            row.cohort,
          card,
          "help",
        );
      }
      const table = node("table", "", $("forecast-evaluation"));
      node(
        "caption",
        "Archived-weather issued-policy skill; live skill is unverified.",
        table,
      );
      const header = node("tr", "", node("thead", "", table));
      for (const h of [
        "Horizon",
        "RMSE (µg/m³)",
        "MAE (µg/m³)",
        "Mean bias (µg/m³)",
        "Skill vs persistence",
      ])
        node("th", h, header);
      const body = node("tbody", "", table);
      for (const result of evaluation.results) {
        const score = result.models.prediction;
        const tr = node("tr", "", body);
        for (const text of [
          "+" + result.horizon,
          num(score.rmse, 2),
          num(score.mae, 2),
          num(score.mean_bias, 2),
          num(score.skill_vs_persistence, 3),
        ])
          node("td", text, tr);
      }
    } catch (error) {
      if (request === activeRequest)
        $("forecast-status").textContent = error.message;
    }
  }
  city.addEventListener("change", load);
  load();
})();
