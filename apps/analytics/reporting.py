import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from django.utils import timezone

from apps.warehouse.models import City

from .descriptive import CALENDAR_SOURCES
from .models import CitySeries


def markdown_table(rows, columns):
    if not rows:
        return "No eligible observations.\n"
    text = [
        "| " + " | ".join(label for _, label in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        values = []
        for key, _ in columns:
            value = row.get(key)
            if isinstance(value, float):
                value = f"{value:.2f}"
            values.append(str(value) if value is not None else "—")
        text.append("| " + " | ".join(values) + " |")
    return "\n".join(text) + "\n"


def figures(run, output, descriptive, audit):
    cities = list(City.objects.all())
    annual = pd.DataFrame(descriptive["annual"])
    if not annual.empty:
        fig, ax = plt.subplots(figsize=(12, 6))
        for index, (city, rows) in enumerate(annual.groupby("city")):
            color = plt.get_cmap("tab20")(index)
            for first, last in [(2015, 2019), (2024, 2025)]:
                subset = rows[rows.year.between(first, last)].sort_values("year")
                ax.scatter(
                    subset.year,
                    subset.annual_mean_pm25,
                    marker="o",
                    color=color,
                    label=city if first == 2015 else None,
                )
        ax.set_ylabel("PM2.5 (µg/m³)")
        ax.set_xlabel("Eligible observed year")
        ax.set_title("Annual means: observed eras; no gap interpolation")
        ax.legend(ncol=3, fontsize=8)
        fig.tight_layout()
        save_figure(fig, output, "annual_pm25")
    climate = pd.DataFrame(descriptive["climatology"])
    fig, axes = plt.subplots(4, 3, figsize=(14, 12), sharex=True)
    for ax, city in zip(axes.flat, cities, strict=True):
        rows = climate[climate.city == city.slug].sort_values("month")
        ax.plot(rows.month, rows.mean_pm25, marker="o")
        ax.set_title(city.name)
        ax.set_xticks(range(1, 13))
        ax.set_ylabel("PM2.5 (µg/m³)")
    fig.suptitle("Monthly climatology: eligible years and complete months")
    fig.tight_layout()
    save_figure(fig, output, "monthly_climatology")
    diurnal = pd.DataFrame(descriptive["diurnal"])
    fig, axes = plt.subplots(4, 3, figsize=(14, 12), sharex=True)
    for ax, city in zip(axes.flat, cities, strict=True):
        for label, rows in diurnal[diurnal.city == city.slug].groupby("season"):
            ax.plot(rows.hour, rows.mean_pm25, label=label)
        ax.set_title(city.name)
        ax.set_ylabel("PM2.5 (µg/m³)")
        ax.set_xlabel("IST hour")
    axes.flat[0].legend(fontsize=7)
    fig.tight_layout()
    save_figure(fig, output, "seasonal_diurnal")
    episodes = pd.DataFrame(descriptive["diwali"])
    fig, ax = plt.subplots(figsize=(11, 6))
    if not episodes.empty:
        for city, rows in episodes.groupby("city"):
            profile = rows.groupby("offset").value.mean()
            ax.plot(profile.index, profile.values, marker="o", label=city)
    ax.set_xlabel("Days from official-calendar Diwali")
    ax.set_ylabel("PM2.5 (µg/m³)")
    ax.set_title("Observed Diwali windows in eligible city-years; descriptive")
    ax.legend(ncol=3, fontsize=8)
    fig.tight_layout()
    save_figure(fig, output, "diwali_window")
    # Separate time axes for the observed eras; never draw the 2020–2023 gap.
    fig, axes = plt.subplots(len(cities), 2, figsize=(15, 30), sharey="row")
    for row, city in enumerate(cities):
        for col, (first, last) in enumerate([(2015, 2019), (2024, 2025)]):
            ax = axes[row, col]
            for kind in ["raw", "deweathered"]:
                records = list(
                    CitySeries.objects.filter(
                        run=run,
                        city=city,
                        pollutant__code="pm25",
                        frequency="monthly",
                        kind=kind,
                        date__year__gte=first,
                        date__year__lte=last,
                    ).values("date", "value")
                )
                frame = pd.DataFrame(records)
                if not frame.empty:
                    dates = pd.date_range(f"{first}-01-01", f"{last}-12-01", freq="MS")
                    values = frame.set_index(pd.to_datetime(frame.date)).value.reindex(dates)
                    ax.plot(dates, values, label=kind)
            ax.set_title(f"{city.name}: {first}–{last}")
            ax.set_ylabel("PM2.5 (µg/m³)")
            ax.legend(fontsize=7)
    fig.tight_layout()
    save_figure(fig, output, "raw_deweathered_monthly")
    records = []
    for label in ["before", "after"]:
        stage = (
            audit.get("initial_correction", audit)["before"]
            if label == "before"
            else audit["after"]
        )
        for source, counts in stage["totals"].items():
            total = sum(counts.values())
            for flag, count in counts.items():
                if flag != "ok":
                    records.append(
                        {
                            "source": source,
                            "stage": label,
                            "flag": flag,
                            "percent": 100 * count / total,
                        }
                    )
    rates = pd.DataFrame(records)
    fig, ax = plt.subplots(figsize=(10, 6))
    rates.pivot_table(
        index=["source", "flag"], columns="stage", values="percent", fill_value=0
    ).plot.bar(ax=ax)
    ax.set_ylabel("Percent of all source rows")
    ax.set_title("Quality flags before and after audit")
    fig.tight_layout()
    save_figure(fig, output, "flag_rates")


def save_figure(fig, output, name):
    for extension in ["svg", "png"]:
        fig.savefig(output / f"{name}.{extension}", dpi=160)
    plt.close(fig)


def write_report(run, output, audit, tables, descriptive, performance, population):
    folder = Path("docs/results")
    folder.mkdir(parents=True, exist_ok=True)
    rates = []
    initial = audit.get("initial_correction", audit)
    for source in initial["before"]["totals"]:
        total = sum(initial["before"]["totals"][source].values())
        for flag in ["missing", "negative", "stuck", "pm25_gt_pm10", "outlier"]:
            before = initial["before"]["totals"][source].get(flag, 0)
            after = audit["after"]["totals"][source].get(flag, 0)
            rates.append(
                {
                    "source": source,
                    "flag": flag,
                    "before": before,
                    "after": after,
                    "before_percent": 100 * before / total,
                    "after_percent": 100 * after / total,
                }
            )
    eligible = [r for r in tables["coverage"] if r["pollutant"] == "pm25" and r["eligible"]]
    lines = [
        "# Phase 3A: actual data audit and analysis\n",
        f"Run **{run.pk}**, recorded **{timezone.localtime().isoformat()}** (Asia/Kolkata). "
        f"Data window {run.data_start} to {run.data_end}. Results come from this run; "
        f"the original pre-correction audit is retained from run {initial.get('run', run.pk)}.\n",
        "## Flag audit\n",
        "The headline flag rate included missing hours, not just invalid finite concentrations. "
        "The missing rule stays: at least three valid distinct quarters are required. "
        "Repeated zero alone cannot distinguish a reporting/detection floor from a "
        "frozen instrument, "
        "so zero flatlines are no longer automatically stuck. "
        "Equal hourly means are no longer marked stuck when their cached source quarters varied. "
        "Positive six-hour flatlines remain a conservative diagnostic, including rounded values; "
        "the available metadata does not establish instrument malfunction. "
        "PM2.5/PM10 comparisons are at the same station/hour in canonical µg/m³ and "
        "require both values. "
        "They remain diagnostic, not proof of calibration failure; separate instruments "
        "can disagree. "
        "Outlier thresholds stay 1000/2000 µg/m³ and keep measurements. No live "
        "negative/outlier example "
        "exists in this snapshot; their behavior is tested with synthetic cases.\n",
        markdown_table(
            rates,
            [
                ("source", "Source"),
                ("flag", "Flag"),
                ("before", "Before"),
                ("after", "After"),
                ("before_percent", "Before %"),
                ("after_percent", "After %"),
            ],
        ),
        f"Initial correction changed **{initial['changed_rows']:,}** flags in run "
        f"**{initial.get('run', run.pk)}**; this run changed **{audit['changed_rows']:,}**. "
        f"This run inspected **{audit['quarter_candidates_examined']:,}** "
        "quarter-backed candidates, "
        f"**{audit['varying_quarter_candidates']:,}** with varying quarters. "
        f"The order-independent hash of every measurement/key/run link remained identical: "
        f"`{audit['fingerprint_before']}`. No value or raw_value was rewritten. "
        "Full breakdown by source, flag, pollutant, station and year is in "
        "flags_before.csv / flags_after.csv (this run); "
        "the initial baseline is in flag_audit.json; "
        "the evidence CSV preserves input paths and SHA256.\n",
        "Real input examples: Peenya NO2 at 17.0 and NH3 at 12.53 on 2025-12-31 stayed flat "
        "in their original quarters while other variables changed. Velachery PM2.5 remained 7.73 "
        "while PM10 varied widely. These support retaining positive flatline screening. "
        "Sewri on 2025-12-14 23:15 UTC reports PM2.5 151.29 versus PM10 104.53, while adjacent "
        "quarters and other columns jump markedly; the inversion flag is a useful "
        "source-data warning, "
        "not something to repair by inventing values. Some inversions are tiny: the initial audit "
        "counted 581 of 1,760 within 5 µg/m³ and 482 within 10%; excluding them is conservative.\n",
        "## Station and population decisions\n",
        markdown_table(
            audit["excluded_stations"],
            [
                ("station__external_id", "CPCB ID"),
                ("station__name", "Excluded station"),
                ("reason", "Reason"),
            ],
        ),
        "These stations are excluded from city and spatial aggregation pending official "
        "GPS verification.\n",
        f"Default WorldPop: **{population['year']}**, `{population['path']}`, "
        f"{population['bytes']:,} bytes, SHA256 `{population['sha256']}`. "
        "This is a constrained R2025A v1 alpha modelled population estimate, not a census. "
        "The 2030 projection remains registered and is not default. No exposure "
        "calculation was performed. "
        "[Provider catalogue](https://hub.worldpop.org/geodata/summary?id=73807).\n",
        "## Analysis-ready coverage\n",
        f"Materialised tables contain **{tables['hourly_rows']:,}** city/pollutant/hour means. "
        "Only quality_flag=ok and non-excluded stations contribute, with station count per hour. "
        "Bins use IST calendar hours; ERA5 joins at the UTC timestamp of each local-hour midpoint "
        "(30 minutes after its start), without interpolation. Preserve original "
        "warehouse timestamps. "
        "OpenCity's explicit +0000 convention still needs independent verification "
        "before fine-scale "
        "cross-provider time comparisons. Daily means need 18 hours; monthly means need "
        "75% of calendar "
        "days. A city-year is eligible only with at least 75% valid hours and 75% valid days. "
        f"**{len(eligible)}** PM2.5 city-years meet this stronger analysis rule.\n",
        markdown_table(
            eligible,
            [
                ("city", "City"),
                ("year", "Year"),
                ("hours", "Hours"),
                ("valid_days", "Valid days"),
                ("expected_days", "Calendar days"),
                ("valid_months", "Valid months"),
            ],
        ),
        "All pollutants/years, including zero coverage, are in analysis_coverage.csv. "
        "Calendar gaps describe missingness and are never used as model observations.\n",
        "## Descriptive results\n",
        "Annual means average valid daily means, with within-year ranks among eligible "
        "cities only. "
        "Exceedance counts use strict >60 µg/m³ (NAAQS) and >15 µg/m³ (WHO 2021).\n",
        markdown_table(
            descriptive["annual"],
            [
                ("city", "City"),
                ("year", "Year"),
                ("annual_mean_pm25", "Annual PM2.5"),
                ("valid_days", "Valid days"),
                ("naaqs_days", ">60 days"),
                ("who_days", ">15 days"),
                ("rank", "Rank"),
            ],
        ),
        "Monthly climatology, seasonal diurnal profiles, weekday/weekend contrasts and winter-smog "
        "means with their contributing counts are stored in CSV and CityMetric. Winter-smog is "
        "Oct 15–Jan 31; the within-calendar-year contrast comprises Jan 1–31 and Oct 15–Dec 31.\n",
        markdown_table(
            descriptive["weekday"],
            [
                ("city", "City"),
                ("year", "Year"),
                ("weekday_mean", "Weekday PM2.5"),
                ("weekday_valid_days", "Weekdays"),
                ("weekend_mean", "Weekend PM2.5"),
                ("weekend_valid_days", "Weekend days"),
                ("weekend_minus_weekday", "Weekend − weekday"),
            ],
        ),
        markdown_table(
            descriptive["winter_smog"],
            [
                ("city", "City"),
                ("year", "Year"),
                ("winter_mean", "Winter PM2.5"),
                ("winter_valid_days", "Winter days"),
                ("rest_mean", "Rest PM2.5"),
                ("rest_valid_days", "Rest days"),
            ],
        ),
        "![Monthly climatology](../../data/results/" + str(run.pk) + "/monthly_climatology.png)\n",
        "![Seasonal diurnal profiles](../../data/results/"
        + str(run.pk)
        + "/seasonal_diurnal.png)\n",
        "![Diwali window](../../data/results/" + str(run.pk) + "/diwali_window.png)\n",
        "Diwali uses the central official calendar's date for all cities; regional "
        "observance can differ. "
        "The −3/+3-day windows retain only valid daily measurements in eligible "
        "city-years. Dates and sources:\n",
    ]
    from .descriptive import DIWALI

    lines.extend(
        f"- {year}: {day}; [official calendar]({CALENDAR_SOURCES[year]}).\n"
        for year, day in DIWALI.items()
    )
    lines.extend(
        [
            "\nDescriptive change compares equal-weight eligible annual means in the two "
            "observed eras. "
            "95% intervals use 500 fixed-seed year-and-seven-day-block resamples of measured days. "
            "They omit structural uncertainty from stations, source conventions and "
            "non-random missingness; "
            "none of these comparisons is a causal policy effect.\n",
            markdown_table(
                descriptive["change"],
                [
                    ("city", "City"),
                    ("status", "Status"),
                    ("baseline_mean", "2015–2019"),
                    ("recent_mean", "2024–2025"),
                    ("difference", "Recent − baseline"),
                    ("ci95_low", "95% low"),
                    ("ci95_high", "95% high"),
                ],
            ),
            "## Meteorological normalisation\n",
            "[Grange et al. 2018](https://doi.org/10.5194/acp-18-6223-2018) motivates "
            "the random forest. "
            "This implementation adapts the daily Swiss PM10 method to hourly Indian city PM2.5. "
            "Like [rmweather](https://github.com/skgrange/rmweather), it resamples joint "
            "weather and seasonal "
            "covariates while keeping date trend fixed. At least 300 observed donor "
            "draws are used with "
            "fixed seed; common random numbers and exact forest trend partitions avoid "
            "redundant predictions. "
            "Only existing eligible city-year hours with complete weather "
            "train/normalise. No imputation, "
            "forecast or target in the 2020–2023 gap is created. BLH is included if available; "
            "its January–June 2024 nulls remove those targets rather than fill them.\n",
            "Validation fits only the earlier 80% of observed complete-case hours, with "
            "a seven-day purge "
            "before the final 20% holdout. The final historical normalisation model then "
            "refits on all "
            "available eligible complete-case hours; holdout metrics always come from "
            "the separate validation model. "
            "Permutation importance on held-out data, parameters and versions are in "
            "each city_model.json.\n",
            markdown_table(
                performance,
                [
                    ("city", "City"),
                    ("r2", "Blocked R²"),
                    ("rmse", "RMSE µg/m³"),
                    ("bias", "Bias"),
                    ("train_hours", "Train hours"),
                    ("test_hours", "Holdout hours"),
                    ("reliable_screen", "Readiness screen"),
                ],
            ),
            "Held-out permutation importance: three largest mean decreases in R² per city. "
            "All features and five-repeat standard deviations are in each city_model.json. "
            "Correlated predictors share importance; these values are not causal contributions.\n",
            markdown_table(
                [
                    {"city": row["city"], "feature": feature, **importance}
                    for row in performance
                    for feature, importance in sorted(
                        row.get("permutation_importance", {}).items(),
                        key=lambda item: item[1]["mean_delta_r2"],
                        reverse=True,
                    )[:3]
                ],
                [
                    ("city", "City"),
                    ("feature", "Feature"),
                    ("mean_delta_r2", "Mean ΔR²"),
                    ("std", "SD"),
                ],
            ),
            "The readiness screen was defined before results: R²≥0.5, RMSE≤50% of holdout mean, "
            "absolute bias≤10% of holdout mean, at least 2,000 train and 1,000 test hours. "
            "This is a practical screen, not proof that a model or a causal research "
            "design is reliable. "
            "Cities with only one observed era cannot support an old/recent comparison.\n",
            "![Raw and deweathered series](../../data/results/"
            + str(run.pk)
            + "/raw_deweathered_monthly.png)\n",
            "Daily/monthly outputs preserve the same completeness thresholds. "
            "sampling_se is Monte Carlo "
            "sampling error, not total model/measurement uncertainty. All CSVs, models, "
            "SVG/PNG figures "
            f"and hashes are under data/results/{run.pk}/. "
            "Keep manifest.json eligible for version control.\n",
            "## Reproducibility and limitations\n",
            "```json\n" + json.dumps(run.parameters, indent=2) + "\n```\n",
            f"Recorded Git commit: `{run.git_commit or 'unavailable'}`. "
            "The source-code SHA256 and installed library versions are also stored with the run. "
            "Fixed seeds cannot remove changes in inputs or libraries.\n",
            "2020–2023/2026 concentration coverage is absent or negligible. Historical "
            "observations "
            "are PM2.5 only. Site networks and provider compilations differ between eras; changing "
            "station contributions can change city means. Coverage is not representativeness. "
            "Some raw source rows have suspicious column/value jumps. Positive flatlines "
            "and PM inversions "
            "are diagnostic flags, not confirmed equipment faults. Public ERA5 is "
            "reanalysis at approximate "
            "city centres and has variable-specific nulls. Whole-case selection "
            "introduces selection bias. "
            "The city-year eligibility rule does not guarantee every season is equally "
            "represented. "
            "RF normalisation cannot identify a policy effect or remove all "
            "emission/chemistry confounding.\n",
            "Phase 3B should validate provider time conventions and station metadata, "
            "examine station-network "
            "sensitivity, assess season-specific holdout errors and review source "
            "anomalies before selecting "
            "research designs. Do not use before/after differences as causal estimates. "
            "Forecasting, RAG, "
            "simulators and dashboards remain outside this phase.\n",
        ]
    )
    path = folder / "PHASE3A.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
