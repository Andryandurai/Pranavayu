"""Export measured Phase 3A2 diagnostics and figures without changing model results."""

import csv
import hashlib
import json
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from django.conf import settings

from apps.warehouse.models import Station

from .aggregation import aggregate_daily, aggregate_monthly
from .diagnostic_pipeline import save
from .lifecycle import code_metadata
from .models import AnalysisRun


def fmt(value, places=3):
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "unavailable"
    return f"{value:.{places}f}" if isinstance(value, (float, np.floating)) else str(value)


def table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines.extend("| " + " | ".join(str(v).replace("|", "/") for v in row) + " |" for row in rows)
    return "\n".join(lines)


def hyderabad_raw_audit(data, output):
    results = []
    for path in sorted((Path(settings.RAW_DATA_ROOT) / "opencity/hyderabad").glob("*.csv")):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            headers = next(csv.reader(handle))
        if "Timestamp" not in headers:
            continue
        column = next(h for h in headers if h.startswith("PM2.5 ("))
        rows = pd.read_csv(path, usecols=["Timestamp", "Station ID", "Station Name", column])
        # Verified publisher wall clock: stripping the incorrect offset restores IST dates.
        rows = rows[rows.Timestamp.str.startswith("2025-")].copy()
        rows = rows.drop_duplicates(["Station ID", "Timestamp"])
        values = pd.to_numeric(rows[column], errors="coerce").dropna()
        if values.empty:
            continue
        site = rows["Station ID"].iloc[0]
        maximum = float(values.max())
        longest, streak, previous = 0, 0, None
        for value in rows[column]:
            streak = streak + 1 if pd.notna(value) and value == previous else 1
            longest = max(longest, streak) if pd.notna(value) else longest
            previous = value
        results.append(
            dict(
                site=site,
                station=rows["Station Name"].iloc[0],
                declared_unit=column.split("(", 1)[1].rstrip(")"),
                quarters=len(rows),
                finite_quarters=len(values),
                raw_quarter_max=maximum,
                quarter_count_at_max=int((values == maximum).sum()),
                quarter_fraction_integer=float(np.isclose(values, values.round()).mean()),
                distinct_quarter_values=int(values.nunique()),
                longest_equal_run_quarters=longest,
                path=str(path.relative_to(settings.RAW_DATA_ROOT)),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )
    raw = pd.DataFrame(results)
    raw.to_csv(output / "hyderabad_raw_quarters.csv", index=False)
    stations = pd.read_pickle(data / "hyderabad_station_hours.pkl")
    recent = stations[stations.year == 2025].copy()
    daily_records = []
    for (site, name), group in recent.groupby(["external_id", "name"]):
        days = aggregate_daily(
            group, pd.Timestamp("2025-01-01").date(), pd.Timestamp("2025-12-31").date()
        )
        days = days.dropna(subset=["value"])
        daily_records.append(
            dict(
                site=site,
                station=name,
                valid_days=len(days),
                daily_max=float(days.value.max()),
                days_above_60=int((days.value > 60).sum()),
            )
        )
    daily = pd.DataFrame(daily_records)
    daily.to_csv(output / "hyderabad_station_daily.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sorted_raw = raw.sort_values("raw_quarter_max")
    axes[0].barh(sorted_raw.site, sorted_raw.raw_quarter_max)
    axes[0].set_xlabel("Published quarter PM2.5 maximum (ug/m3)")
    axes[0].set_title("Hyderabad 2025: unfiltered source quarters")
    city = pd.read_csv(data / "hyderabad_raw_daily.csv")
    city = city[pd.to_datetime(city.date).dt.year == 2025]
    axes[1].plot(pd.to_datetime(city.date), city.value, label="Quality-screened city daily mean")
    axes[1].axhline(60, color="red", linestyle="--", label="60 ug/m3")
    axes[1].set_ylabel("PM2.5 (ug/m3)")
    axes[1].legend()
    save(fig, output, "hyderabad_sanity")
    return raw, daily


def geography_figures(data, output):
    geo = pd.read_csv(data / "station_geography.csv")
    grids = json.loads((data / "weather_grids.json").read_text())
    positions = {s.pk: (s.location.x, s.location.y) for s in Station.objects.all()}
    fig, axes = plt.subplots(3, 4, figsize=(16, 12))
    summaries = []
    for ax, grid in zip(axes.flat, grids, strict=True):
        rows = geo[geo.city == grid["city"]]
        points = np.array([positions[i] for i in rows.station_id])
        ax.scatter(
            points[:, 0],
            points[:, 1],
            c=np.where(rows.inside_city_district, "tab:blue", "tab:red"),
            s=20,
        )
        ax.scatter(grid["requested_lon"], grid["requested_lat"], marker="x", color="black", s=70)
        returned = np.array(grid["returned_grid_points"])
        if len(returned):
            ax.scatter(returned[:, 0], returned[:, 1], marker="*", color="green", s=80)
        ax.set_title(grid["city"])
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        summaries.append(
            [
                grid["city"],
                len(rows),
                int(rows.inside_city_district.sum()),
                int(rows.actual_districts.notna().sum()),
                fmt(rows.requested_point_distance_km.min(), 2),
                fmt(rows.requested_point_distance_km.max(), 2),
                fmt(rows.grid_point_distance_km.max(), 2),
            ]
        )
    fig.suptitle(
        "Blue: assigned district; red: another district. Black x: request; green star: ERA5 grid"
    )
    save(fig, output, "station_weather_points")
    network = pd.read_csv(data / "stations_by_year.csv")
    counts = network.groupby(["city", "year"]).site.nunique().unstack().fillna(0).astype(int)
    fig, ax = plt.subplots(figsize=(12, 7))
    image = ax.imshow(counts.to_numpy(), aspect="auto", cmap="Blues")
    ax.set_xticks(range(len(counts.columns)), counts.columns)
    ax.set_yticks(range(len(counts.index)), counts.index)
    for i in range(len(counts)):
        for j in range(len(counts.columns)):
            ax.text(j, i, str(counts.iloc[i, j]), ha="center", va="center")
    fig.colorbar(image, ax=ax, label="Contributing physical CPCB sites")
    save(fig, output, "station_network_years")
    counts.to_csv(output / "station_counts_by_year.csv")
    return geo, summaries, counts


def model_figures(summary, original, comparisons, data, output):
    cities = [r["city"] for r in summary]
    variants = list(dict.fromkeys(r["variant"] for r in comparisons))
    matrix = np.array(
        [
            [
                next(r["selection_r2"] for r in comparisons if r["city"] == c and r["variant"] == v)
                for v in variants
            ]
            for c in cities
        ]
    )
    fig, ax = plt.subplots(figsize=(14, 8))
    image = ax.imshow(matrix, aspect="auto", cmap="RdYlGn", vmin=0, vmax=1)
    ax.set_xticks(range(len(variants)), variants, rotation=25, ha="right")
    ax.set_yticks(range(len(cities)), cities)
    for i in range(len(cities)):
        for j in range(len(variants)):
            ax.text(j, i, fmt(matrix[i, j], 2), ha="center", va="center", fontsize=8)
    fig.colorbar(image, ax=ax, label="Mean within-period daily OOF R2 on common dates")
    save(fig, output, "model_structure_comparison")
    fig, ax = plt.subplots(figsize=(13, 5))
    for offset, scheme in enumerate(["random", "weeks", "transfer"]):
        values = [
            next(r["native"]["r2"] for r in original if r["city"] == c and r["scheme"] == scheme)
            for c in cities
        ]
        ax.bar(
            np.arange(len(cities)) + (offset - 1) * 0.25,
            [v if v is not None else np.nan for v in values],
            width=0.25,
            label=scheme,
        )
    ax.set_xticks(range(len(cities)), cities, rotation=30, ha="right")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_ylabel("Hourly R2 (original predictors and original timestamps)")
    ax.legend()
    save(fig, output, "validation_design_comparison")
    for result in summary:
        city = result["city"]
        monthly = pd.read_csv(output.parent / f"{city}_residual_month.csv")
        seasonal = pd.read_csv(output.parent / f"{city}_residual_season.csv")
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        for period, rows in monthly.groupby("period"):
            axes[0].plot(rows.month, rows.nmb_percent, marker="o", label=period)
        for period, rows in seasonal.groupby("period"):
            axes[1].plot(rows.season, rows.nmb_percent, marker="o", label=period)
        for ax in axes:
            ax.axhline(20, color="red", linestyle="--")
            ax.axhline(-20, color="red", linestyle="--")
            ax.set_ylabel("OOF normalised mean bias (%)")
            ax.legend()
        axes[0].set_xlabel("IST calendar month")
        axes[1].tick_params(axis="x", rotation=15)
        fig.suptitle(city + ": final selected model residuals")
        save(fig, output, city + "_residuals")
        raw = pd.read_csv(data / f"{city}_raw_daily.csv")
        normalised = pd.read_csv(output.parent / f"{city}_deweathered_daily.csv")
        fig, axes = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
        for ax, (first, last) in zip(axes, [(2015, 2019), (2024, 2025)], strict=True):
            for label, rows in [("raw", raw), ("common-reference normalised", normalised)]:
                rows = rows[pd.to_datetime(rows.date).dt.year.between(first, last)].copy()
                if rows.empty:
                    continue
                rows["date"] = pd.to_datetime(rows.date).dt.date
                first_day, last_day = (
                    pd.Timestamp(f"{first}-01-01").date(),
                    pd.Timestamp(f"{last}-12-31").date(),
                )
                calendar = pd.date_range(first_day, last_day).date
                rows = rows.set_index("date").reindex(calendar).rename_axis("date").reset_index()
                months = aggregate_monthly(rows, first_day, last_day)
                ax.plot(pd.to_datetime(months.date), months.value, label=label)
            ax.set_xlim(pd.Timestamp(f"{first}-01-01"), pd.Timestamp(f"{last}-12-31"))
            ax.set_title(f"{city}, {first}-{last}")
            ax.set_ylabel("PM2.5 (ug/m3)")
            ax.legend()
        save(fig, output, city + "_normalisation")


def interval_rows(changes):
    rows = []
    for row in changes.to_dict("records"):
        if row["status"] != "descriptive":
            continue
        rows.append(
            [
                row["city"],
                row["series"],
                fmt(row["baseline_mean"]),
                fmt(row["recent_mean"]),
                fmt(row["difference"]),
                f"[{fmt(row['ci95_low'])}, {fmt(row['ci95_high'])}]",
            ]
        )
    return rows


def update_manifest(run, output):
    path = output / "manifest.json"
    manifest = json.loads(path.read_text())
    commit, metadata = code_metadata()
    manifest["export_revision"] = dict(git_commit=commit, **metadata)
    files = []
    for item in sorted(output.rglob("*")):
        if item.is_file() and item.name != "manifest.json":
            with item.open("rb") as handle:
                digest = hashlib.file_digest(handle, "sha256").hexdigest()
            files.append(
                dict(
                    path=item.relative_to(output).as_posix(),
                    bytes=item.stat().st_size,
                    sha256=digest,
                )
            )
    manifest["files"] = files
    path.write_text(json.dumps(manifest, indent=2))
    run.results["export_revision"] = manifest["export_revision"]
    run.save(update_fields=["results"])


def export_report(run_id):
    run = AnalysisRun.objects.get(pk=run_id, name="phase3a2", status="success")
    root = Path(settings.BASE_DIR)
    output = root / "data/results" / str(run_id)
    data = root / "data/results" / str(run.parameters["data_run"])
    figures = output / "diagnostics"
    figures.mkdir(exist_ok=True)
    summary = json.loads((output / "readiness.json").read_text())
    original = json.loads((output / "D4_original_validation.json").read_text())
    comparisons = json.loads((output / "D5_comparisons.json").read_text())
    changes = pd.read_csv(output / "old_recent_differences.csv")
    geo, geo_summary, network = geography_figures(data, figures)
    hyde_raw, hyde_days = hyderabad_raw_audit(data, figures)
    model_figures(summary, original, comparisons, data, figures)
    proof = json.loads((root / "docs/results/PHASE3A2_CLOCK_PROOF.json").read_text())
    for record in proof["records"]:
        source = root / record["independent_csv"]
        shutil.copyfile(source, figures / source.name)
    (figures / "clock_proof.json").write_text(json.dumps(proof, indent=2))
    lags = pd.read_csv(data / "alignment_summary.csv")
    nulls = pd.read_csv(data / "weather_nulls.csv")
    hyde = json.loads((data / "hyderabad_sanity.json").read_text())
    panels = json.loads((data / "fixed_panels.json").read_text())
    lines = [
        "## Actual diagnostics and results",
        (
            f"Model AnalysisRun **{run.pk}** finished **{run.finished_at.isoformat()}**; "
            f"corrected data run **{run.parameters['data_run']}**, legacy comparison run "
            f"**2**. Original and provisional runs are retained. Compute commit "
            f"`{run.git_commit}`; the immutable protocol JSON hash is "
            f"`{run.parameters['protocol_sha256']}`."
        ),
        "### D1: timestamp alignment",
        (
            "PostgreSQL stores both concentration and weather `observed_at` as timestamp "
            "with time zone and the session is UTC. Open-Meteo requests `timezone=UTC`; "
            "response `utc_offset_seconds=0` is validated. Historical XKDR `collected_at` "
            "is documented as naive IST and is converted to UTC. Recent OpenCity `+0000` "
            "labels contain IST wall clocks: physical times were 5.5 hours late. Same-site "
            "independent hourly comparisons below establish the correction without using "
            "model scores."
        ),
        table(
            ["City", "Station", "Matched hours", "Mean absolute difference", "Maximum difference"],
            [
                [
                    r["city"],
                    r["site"],
                    r["matched_hours"],
                    fmt(r["mean_absolute_difference"], 6),
                    fmt(r["max_absolute_difference"], 6),
                ]
                for r in proof["records"]
            ],
        ),
        (
            "The publisher repository's UTC-label attachment is supporting context, not "
            "independently established lineage for every OpenCity file. The direct "
            "value-and-clock matches are the decisive evidence. Independent-source CSVs and "
            "hashes are preserved with this run. [XKDR clock "
            "documentation](https://github.com/xKDR/Air-Quality-Database/"
            "blob/main/docs/PUBLIC_API.md), "
            "[publisher processing "
            "context](https://github.com/Vonter/india-cpcb-aqi/blob/a58f47848e678c7cea58a69758343d08d0b49915/parse.py#L100-L114)."
        ),
        (
            "The original quarter aggregator used UTC bins, then the city builder "
            "relabelled their start as an IST hour. This is wrong for literal UTC quarters "
            "because IST has a half-hour offset. The literal-UTC reconstruction was "
            "retained as sensitivity data run 4. Once the publisher's IST clock is decoded, "
            "its four quarter-hour readings form native IST hours directly; those audited "
            "stored means can be reused after shifting their derived timestamps. Raw "
            "observation times and values remain immutable; consumers of raw warehouse "
            "times must apply the documented clock correction, or use the corrected "
            "analysis snapshot. Weather joins the native IST-hour midpoint, which is a UTC "
            "clock hour."
        ),
        (
            "Lag is Pearson r(PM anomaly at t, wind anomaly at t+lag), calculated on actual "
            "timestamp pairs over -12 to +12 hours after removing period/month/IST-hour "
            "climatology. PM often anticorrelates with wind, so maximum signed r can be the "
            "least-negative boundary value. Both the requested signed maximum and strongest "
            "absolute correlation are reported; a nonzero lag alone is not proof of clock "
            "error."
        ),
        table(
            ["City", "Era", "Max signed lag/r", "Strongest lag/r", "r at zero"],
            [
                [
                    r.city,
                    r.period,
                    f"{r.max_signed_lag}/{fmt(r.max_signed_r)}",
                    f"{r.strongest_lag}/{fmt(r.strongest_r)}",
                    fmt(r.zero_lag_r),
                ]
                for r in lags[lags.stage == "corrected IST"].itertuples()
            ],
        ),
        (
            "Each city's before/after PM2.5-temperature-BLH diurnal plot and complete lag "
            "curve are in the data-run artifacts; BLH-null hours are omitted from BLH "
            "averages and wind is available as the fallback. See the figure index below."
        ),
        "### D2: station locations and weather grids",
        table(
            [
                "City",
                "Station records",
                "Inside assigned district",
                "Inside any district",
                "Request distance min km",
                "Request distance max km",
                "ERA5 grid distance max km",
            ],
            geo_summary,
        ),
        (
            f"There are **{len(geo)}** provider-specific station records. The complete "
            f"per-station positions/containment/distance results are in "
            f"`station_geography.csv`. Assigned district is not a metropolitan-city "
            f"boundary: Delhi uses New Delhi, Chennai and Hyderabad include neighbouring "
            f"districts, and Mumbai uses the historical Mumbai district. "
            f"Out-of-assigned-district locations are reported, not silently relocated or "
            f"excluded. Existing five unverified-GPS exclusions remain. Returned ERA5 grid "
            f"points differ from requested city centres; a single point cannot resolve all "
            f"station meteorology."
        ),
        "### D3: station network changes",
        table(
            ["City"] + [str(y) for y in network.columns],
            [[city] + list(row) for city, row in network.iterrows()],
        ),
        (
            "Counts require a quality-OK PM2.5 station hour; missing or invalid records do "
            "not count as contributing. `stations_by_year.csv` lists every physical CPCB "
            "ID/name/source/year, contributing hours and first/last timestamps. The fixed "
            "panel matches exact CPCB site IDs across providers and requires at least one "
            "valid observation in each era; year-level coverage is then enforced before "
            "comparing. Presence in both eras does not mean every station reports every day."
        ),
        table(["City", "Shared physical stations"], [[p["city"], p["count"]] for p in panels]),
        "### D4: validation design",
        (
            "Phase 3A used the terminal chronological holdout documented above. The "
            "following comparisons retain its original predictor structure and original "
            "data, changing only the split. (a) is random hourly 80/20; (b) is five random "
            "whole-week folds within each observed era, with 24-hour embargo; (c) trains "
            "one era and tests the other. Across-gap transfer is diagnostic only and never "
            "a readiness gate. Single-era cities have no transfer test."
        ),
        table(
            [
                "City",
                "a: random hourly R2",
                "b: week hourly R2",
                "c: old to recent R2",
                "c: recent to old R2",
            ],
            [
                [
                    c["city"],
                    fmt(
                        next(
                            r["native"]["r2"]
                            for r in original
                            if r["city"] == c["city"] and r["scheme"] == "random"
                        )
                    ),
                    fmt(
                        next(
                            r["native"]["r2"]
                            for r in original
                            if r["city"] == c["city"] and r["scheme"] == "weeks"
                        )
                    ),
                    fmt(
                        next(
                            r
                            for r in original
                            if r["city"] == c["city"] and r["scheme"] == "transfer"
                        )["native_periods"]
                        .get("recent", {})
                        .get("r2")
                    ),
                    fmt(
                        next(
                            r
                            for r in original
                            if r["city"] == c["city"] and r["scheme"] == "transfer"
                        )["native_periods"]
                        .get("old", {})
                        .get("r2")
                    ),
                ]
                for c in summary
            ],
        ),
        "### D5: model structure and method decision",
        (
            "Eight prespecified paired variants compare hourly/daily target, BLH inclusion, "
            "trend inclusion and separate-era/pooled-period models. Forest parameters were "
            "fixed. Selection maximises mean era-specific daily week-CV R2 on the common "
            "valid dates of all eight variants. Readiness then uses every valid "
            "selected-model OOF day in each era. Selection and gating share CV, so the "
            "reported performance is not an untouched final-test estimate. The criteria "
            "were frozen before new fits and were not loosened."
        ),
        table(
            ["City"] + [v["name"] for v in run.parameters["protocol"]["variants"]],
            [
                [r["city"]]
                + [
                    fmt(
                        next(
                            c["selection_r2"]
                            for c in comparisons
                            if c["city"] == r["city"] and c["variant"] == v["name"]
                        )
                    )
                    for v in run.parameters["protocol"]["variants"]
                ]
                for r in summary
            ],
        ),
        (
            "Weather null counts below use all observed weather in the two reference eras, "
            "not just model targets. This distinguishes source missingness from PM "
            "coverage. BLH complete-case models lose the first six months of 2024; "
            "common-date comparison prevents that drop from being treated as better "
            "predictive performance."
        ),
        table(
            ["Era", "Variable", "Hours per city", "Nulls per city", "Null %"],
            [
                [
                    p,
                    v,
                    int(g.hours.iloc[0]),
                    int(g.nulls.iloc[0]),
                    fmt(100 * g.nulls.iloc[0] / g.hours.iloc[0], 2),
                ]
                for (p, v), g in nulls.groupby(["period", "variable"], sort=True)
            ],
        ),
        (
            "For cross-period normalisation, both eras use the identical joint sample of "
            "300 donor rows from complete observed 2015-2019 plus 2024-2025 "
            "weather/calendar features. Period and within-era trend are held fixed; a trend "
            "resets at the era boundary and does not bridge 2020-2023. Separate-era forests "
            "use the same pooled donors. A no-trend model can produce a constant normalised "
            "level within an era because all remaining inputs are resampled; that is "
            "reported rather than hidden. Reference distribution weights available "
            "hourly/daily rows, not eras equally. No model predictions are generated in the "
            "concentration gap."
        ),
        "### Final readiness",
        (
            "R2 below for (b) is daily OOF within each era and drives readiness with "
            "bias/support criteria. (a) and (c) are the selected model's native target "
            "resolution; daily-target models use random days, so the required random-hour "
            "comparison remains in D4. Transfer directions report each destination era "
            "separately. Bias is prediction minus observation; NMB is 100 "
            "sum(error)/sum(observation)."
        ),
        table(
            [
                "City",
                "Design",
                "a native R2",
                "b daily R2 old/recent",
                "c native R2 old-to-recent/recent-to-old",
                "NMB % old/recent",
                "Worst month abs NMB %",
                "Ready",
                "Failures",
            ],
            [
                [
                    r["city"],
                    r["selected_design"]["name"],
                    fmt(r["random"]["native"]["r2"]),
                    "/".join(
                        fmt(
                            next(
                                (p["r2"] for p in r["readiness"]["periods"] if p["period"] == era),
                                None,
                            )
                        )
                        for era in ["old", "recent"]
                    ),
                    "/".join(
                        fmt(r["transfer"]["native_periods"].get(era, {}).get("r2"))
                        for era in ["recent", "old"]
                    ),
                    "/".join(
                        fmt(
                            next(
                                (
                                    p["nmb_percent"]
                                    for p in r["readiness"]["periods"]
                                    if p["period"] == era
                                ),
                                None,
                            ),
                            2,
                        )
                        for era in ["old", "recent"]
                    ),
                    fmt(max(p["max_month_abs_nmb"] for p in r["readiness"]["periods"]), 2),
                    "PASS" if r["readiness"]["passed"] else "FAIL",
                    "; ".join(
                        p["period"] + ": " + ", ".join(p["failures"])
                        for p in r["readiness"]["periods"]
                        if p["failures"]
                    ),
                ]
                for r in summary
            ],
        ),
        (
            "Detailed R2, RMSE, mean bias, NMB, weeks and monthly counts are retained in "
            "each city model JSON and residual CSVs, including fixed-panel readiness "
            "separately. A passed all-station screen does not certify a fixed-panel model "
            "automatically."
        ),
        "### D6: residual seasonality",
        table(
            ["City", "Era", "Season", "OOF days", "Mean bias ug/m3", "NMB %"],
            [
                [r["city"], row.period, row.season, row.n, fmt(row.bias), fmt(row.nmb_percent, 2)]
                for r in summary
                for row in pd.read_csv(output / (r["city"] + "_residual_season.csv")).itertuples()
            ],
        ),
        (
            "Every city has calendar-month, individual-year-month and season residual CSVs "
            "and a residual figure. The frozen monthly gate is checked by month of year "
            "within each era; individual year-month tables disclose shorter-lived bias "
            "rather than pooling it out of sight. No post-result model tuning was done to "
            "erase these failures."
        ),
        "### D7: Hyderabad sanity check",
        (
            f"Corrected 2025 city series: **{hyde['valid_days']}** valid days, daily maximum "
            f"**{fmt(hyde['daily_max'])} ug/m3**, annual mean **{fmt(hyde['annual_mean'])} "
            f"ug/m3**, **{hyde['above_60']}** days above 60, **{hyde['above_15']}** above "
            f"15. This is the equally weighted city daily mean, not the maximum "
            f"station/hour/quarter. The network includes {len(hyde['stations'])} recent "
            f"station records, with "
            f"{next(p['count'] for p in panels if p['city'] == 'hyderabad')} shared physical "
            f"stations across eras."
        ),
        table(
            [
                "Station",
                "Raw quarter max",
                "Repeats at max",
                "Integer %",
                "Longest equal quarter run",
                "Daily max after QA",
                "Station days above 60",
                "Unit",
            ],
            [
                [
                    row.site,
                    fmt(row.raw_quarter_max, 2),
                    row.quarter_count_at_max,
                    fmt(100 * row.quarter_fraction_integer, 1),
                    row.longest_equal_run_quarters,
                    fmt(hyde_days.set_index("site").loc[row.site, "daily_max"], 2)
                    if row.site in set(hyde_days.site)
                    else "unavailable",
                    int(hyde_days.set_index("site").loc[row.site, "days_above_60"])
                    if row.site in set(hyde_days.site)
                    else "unavailable",
                    row.declared_unit,
                ]
                for row in hyde_raw.itertuples()
            ],
        ),
        (
            "The units are concentration units in the column headers, not AQI. Raw quarter "
            "maxima and repeated values are reported before quality screening; station "
            "daily maxima use the unchanged quality rules. Shared legacy stations' "
            "rounded/limited ranges and long repeated runs are a source-quality concern. "
            "The cached inputs establish that these values were published; they do not "
            "prove instrument accuracy or rule out publisher/instrument capping. No "
            "undocumented inverse conversion or fabricated uncapping is applied. Zero "
            "city-average exceedance days is reproducible in this source snapshot, with the "
            "station composition and averaging distinction above; it is not independently "
            "validated as a citywide exposure claim."
        ),
        "### Updated old/recent differences",
        (
            "Values are equally weighted annual means over each series' eligible observed "
            "years; differences are recent minus old. Raw intervals use 500 "
            "year-and-seven-calendar-day block resamples. Normalised intervals use the "
            "frozen conditional construction: normalised daily values plus centred week-CV "
            "residuals, then the same resampling. They exclude forest-refit/parameter, "
            "donor-weather and station-network uncertainty and must not be interpreted as "
            "complete confidence intervals or causal effects. The normalised point estimate "
            "is the pure common-reference forest mean. The fixed panel is fitted separately "
            "using the selected structure and the same reference donors."
        ),
        table(
            [
                "City",
                "Series",
                "Old mean",
                "Recent mean",
                "Difference ug/m3",
                "Bootstrap 95% interval",
            ],
            interval_rows(changes),
        ),
        "### What was wrong and what remains limited",
        (
            "Confirmed corrections: recent publisher clocks were mislabelled UTC; literal "
            "UTC quarter means cannot be relabelled to IST bins; terminal chronological "
            "extrapolation was used as a normalisation-readiness test; an absolute trend "
            "encoded the unobserved gap; BLH missingness removed January-June 2024; "
            "provider-specific station IDs hid common physical panels. The new method uses "
            "verified physical clocks, within-era week CV, explicit periods, shared pooled "
            "reference weather, complete-case disclosure and matched CPCB panels. A failed "
            "criterion remains a failure. Remaining limitations include coarse city "
            "weather, district/metropolitan mismatch, network composition, source "
            "rounding/repeats, incomplete early-era coverage, lack of untouched selection "
            "testing and conditional rather than full model uncertainty."
        ),
        "Cities passing the all-station normalisation screen: **"
        + (", ".join(run.results["passed_cities"]) or "none")
        + "**. Only their observed eligible periods are candidates for Phase 3B; "
        "old/recent questions additionally require both eras and an adequate fixed panel. "
        "No Phase 3B research question has been started.",
        "### Figures and audit artifacts",
        (
            f"Corrected data figures/CSVs: `data/results/{run.parameters['data_run']}/`. "
            f"Model comparisons, readiness JSON, fitted forests, residual tables and "
            f"bootstrap differences: `data/results/{run.pk}/`. Figure exports include "
            f"standalone SVG and PNG, backed by the actual CSV/JSON. Every local result "
            f"artifact is hashed in its manifest."
        ),
        (
            f"[Model "
            f"comparison](../../data/results/{run.pk}/diagnostics/model_structure_comparison.svg), "
            f"[validation "
            f"comparison](../../data/results/{run.pk}/diagnostics/"
            "validation_design_comparison.svg), "
            f"[station weather "
            f"points](../../data/results/{run.pk}/diagnostics/station_weather_points.svg), "
            f"[station "
            f"network](../../data/results/{run.pk}/diagnostics/station_network_years.svg), "
            f"[Hyderabad](../../data/results/{run.pk}/diagnostics/hyderabad_sanity.svg)."
        ),
    ]
    for r in summary:
        city = r["city"]
        lines.append(
            f"- {city}: [diurnal alignment](../../data/results/"
            f"{run.parameters['data_run']}/{city}_alignment_diurnal.svg), "
            f"[residuals](../../data/results/{run.pk}/diagnostics/{city}_residuals.svg), "
            f"[normalisation](../../data/results/{run.pk}/diagnostics/{city}_normalisation.svg)."
        )
    lines.append(
        "\nWarehouse measurement/provenance fingerprint remained unchanged: `"
        + str(
            AnalysisRun.objects.get(pk=run.parameters["data_run"]).results[
                "measurement_fingerprint"
            ]
        )
        + "`."
    )
    report_path = root / "docs/results/PHASE3A2.md"
    frozen = report_path.read_text().split("## Actual diagnostics")[0].rstrip()
    report_path.write_text(frozen + "\n\n" + "\n\n".join(lines) + "\n")
    shutil.copyfile(report_path, output / "PHASE3A2.md")
    update_manifest(run, output)
    return report_path
