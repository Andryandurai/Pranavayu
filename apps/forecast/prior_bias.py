"""Investigate the existing deweathering failures before forecast fitting."""

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from django.conf import settings

from .data import load_hourly, write_json

matplotlib.use("Agg")


def diagnose_prior_bias(output):
    output.mkdir(parents=True, exist_ok=True)
    results = {}
    for city, run in [("delhi", 12), ("pune", 10)]:
        path = settings.BASE_DIR / "data" / "results" / str(run) / f"{city}_nested_oof.csv"
        rows = pd.read_csv(path, parse_dates=["date"])
        rows = rows[rows.period == "recent"].copy()
        rows["error"] = rows.prediction - rows.value
        rows["month"] = rows.date.dt.month
        rows["year_month"] = rows.date.dt.strftime("%Y-%m")
        hourly, source = load_hourly(city)
        local = pd.to_datetime(hourly.observed_at, utc=True).dt.tz_convert("Asia/Kolkata")
        hourly["date"] = local.dt.tz_localize(None).dt.normalize()
        network = hourly.groupby("date").agg(
            mean_stations=("station_count", "mean"), observed_hours=("value", "count")
        )
        rows = rows.join(network, on="date")
        tables = {}
        for name in ("month", "year_month", "chosen_design"):
            summary = (
                rows.groupby(name)
                .apply(
                    lambda g: pd.Series(
                        {
                            "days": len(g),
                            "observed_mean": g.value.mean(),
                            "predicted_mean": g.prediction.mean(),
                            "bias_ug_m3": g.error.mean(),
                            "nmb_percent": 100 * g.error.sum() / g.value.sum(),
                            "rmse": np.sqrt(g.error.pow(2).mean()),
                            "mean_stations": g.mean_stations.mean(),
                        }
                    ),
                    include_groups=False,
                )
                .reset_index()
            )
            summary.to_csv(output / f"{city}_{name}_prior_bias.csv", index=False)
            tables[name] = summary.to_dict("records")
        selected = rows.groupby(["year_month", "chosen_design"]).size().rename("days").reset_index()
        selected.to_csv(output / f"{city}_monthly_design_support.csv", index=False)
        calendar = pd.date_range("2024-01-01", "2025-12-31")
        missing = calendar.difference(rows.date)
        tables["missing_oof_days"] = {
            "total": len(missing),
            "by_month": pd.Series(missing.strftime("%Y-%m")).value_counts().sort_index().to_dict(),
        }
        tables["source"] = {"oof_run": run, "raw": source}
        results[city] = tables
        fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
        monthly = pd.DataFrame(tables["year_month"])
        x = pd.to_datetime(monthly.year_month)
        axes[0].plot(x, monthly.observed_mean, label="Observed daily mean")
        axes[0].plot(x, monthly.predicted_mean, label="Nested deweathering OOF prediction")
        axes[0].set_ylabel("PM2.5 (µg/m³)")
        axes[0].legend(fontsize=8)
        axes[1].bar(x, monthly.nmb_percent, width=20)
        axes[1].axhline(20, color="red", linestyle="--")
        axes[1].axhline(-20, color="red", linestyle="--")
        axes[1].set_ylabel("NMB (%)")
        fig.suptitle(f"{city.title()}: Phase 3B recent monthly bias")
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(output / f"{city}_prior_monthly_bias.png", dpi=150)
        plt.close(fig)
    write_json(output / "prior_bias_findings.json", results)
    lines = [
        "# Delhi and Pune bias investigation before forecasting",
        "",
        "This analysis uses saved Phase 3B outer-fold predictions and raw Run 8 station",
        "support. It makes no new model fit and does not use Phase 4 scores.",
        "",
    ]
    for city, result in results.items():
        lines += [
            f"## {city.title()}",
            "",
            "| Month | OOF days | Observed | Predicted | Bias µg/m³ | NMB % |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for row in result["month"]:
            lines.append(
                f"| {int(row['month'])} | {int(row['days'])} | {row['observed_mean']:.4f} "
                f"| {row['predicted_mean']:.4f} | {row['bias_ug_m3']:.4f} "
                f"| {row['nmb_percent']:.4f} |"
            )
        lines += [
            "",
            f"Missing recent OOF days: {result['missing_oof_days']['total']}. Monthly counts",
            "and inner-selected design/station support are retained in the diagnostic CSVs.",
            "",
        ]
        focus = "-02" if city == "delhi" else "-05"
        for row in result["year_month"]:
            if row["year_month"].endswith(focus):
                lines.append(
                    f"{row['year_month']}: {int(row['days'])} OOF days, "
                    f"bias {row['bias_ug_m3']:.4f} µg/m³, NMB {row['nmb_percent']:.4f}%, "
                    f"mean contributing stations {row['mean_stations']:.4f}."
                )
        lines.append("")
    lines += [
        "Delhi's pooled weather/calendar model overpredicts recent low-pollution months;",
        "the saved design switches between a pooled no-trend daily forest and a BLH",
        "hourly forest. Old-period concentrations enter those pooled fits. This is",
        "consistent with cross-era level/season mixing and regression toward the mean,",
        "but the saved diagnostics do not identify a unique causal mechanism. The BLH",
        "fold excludes early-2024 days. The error is not evidence of a new timestamp",
        "offset: the canonical clock was already independently verified in Phase 3B.",
        "",
        "Pune's failing May bias is a modest absolute overprediction relative to a low",
        "observed mean. BLH-selected folds omit early-2024 support, and the 2024/2025",
        "month-specific CSV distinguishes support from annual bias cancellation. Published",
        "network composition varies; station counts alone cannot attribute the error.",
        "",
        "The forecasting remedy is recent-only raw data, lagged PM, target-date calendar,",
        "issue-safe forecast weather and monthly temporal selection/calibration. Forecast",
        "bias must still be measured; this investigation does not promise it will vanish.",
        "",
    ]
    (settings.BASE_DIR / "docs" / "results" / "PHASE4_BIAS.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    return results
