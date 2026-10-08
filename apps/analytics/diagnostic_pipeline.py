import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from django.db import connection

from apps.warehouse.models import City

from .aggregation import aggregate_daily, aggregate_monthly, analysis_dataframe
from .audit import measurement_fingerprint
from .diagnostic_data import (
    city_hours,
    fixed_panel,
    geography_audit,
    hyderabad_audit,
    join_weather,
    snapshot_city,
    station_hours,
    weather_frame,
)
from .lifecycle import analysis_run
from .model_diagnostics import lag_correlations, period_labels


def save(fig, output, name):
    fig.tight_layout()
    for suffix in ["png", "svg"]:
        fig.savefig(output / f"{name}.{suffix}", dpi=150)
    plt.close(fig)


def alignment_diagnostic(city, frames, output):
    curves, lags, findings = [], [], []
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    for ax in axes.flat:
        ax.set_xlim(0, 23)
    for column, (stage, frame) in enumerate(frames.items()):
        rows = frame.copy()
        local = rows.observed_at.dt.tz_convert("Asia/Kolkata")
        rows["period"] = period_labels(rows.observed_at)
        rows["month"], rows["hour"] = local.dt.month, local.dt.hour
        rows = rows[rows.period != "gap"]
        for index, (period, group) in enumerate(rows.groupby("period")):
            profile = group.groupby("hour").agg(
                value=("value", "mean"),
                temperature_c=("temperature_c", "mean"),
                boundary_layer_height_m=("boundary_layer_height_m", "mean"),
                wind_speed_ms=("wind_speed_ms", "mean"),
            )
            profile.to_csv(output / f"{city.slug}_{stage}_{period}_diurnal.csv")
            ax = axes[index, column]
            ax.plot(profile.index, profile.value, color="black", label="PM2.5")
            ax.set_ylabel("PM2.5 (ug/m3)")
            twin = ax.twinx()
            twin.plot(profile.index, profile.temperature_c, color="red", label="Temperature")
            twin.set_ylabel("Temperature (C)", color="red")
            third = ax.twinx()
            third.spines["right"].set_position(("axes", 1.15))
            variable = (
                "boundary_layer_height_m"
                if profile.boundary_layer_height_m.notna().any()
                else "wind_speed_ms"
            )
            third.plot(profile.index, profile[variable], color="blue")
            third.set_ylabel(
                "BLH (m)" if variable.startswith("boundary") else "Wind (m/s)", color="blue"
            )
            ax.set_title(f"{city.name}: {stage}, {period}")
            ax.set_xlabel("IST hour")
            group = group.copy()
            for feature in ["value", "wind_speed_ms"]:
                group[feature + "_anomaly"] = group[feature] - group.groupby(["month", "hour"])[
                    feature
                ].transform("mean")
            indexed = group.set_index("observed_at")
            table = lag_correlations(indexed.value_anomaly, indexed.wind_speed_ms_anomaly)
            table["city"], table["stage"], table["period"] = city.slug, stage, period
            lags.extend(table.to_dict("records"))
            finite = table.dropna(subset=["correlation"])
            if not finite.empty:
                maximum, strongest = (
                    finite.loc[finite.correlation.idxmax()],
                    finite.loc[finite.correlation.abs().idxmax()],
                )
                findings.append(
                    dict(
                        city=city.slug,
                        stage=stage,
                        period=period,
                        max_signed_lag=int(maximum.lag_hours),
                        max_signed_r=float(maximum.correlation),
                        strongest_lag=int(strongest.lag_hours),
                        strongest_r=float(strongest.correlation),
                        zero_lag_r=float(finite.loc[finite.lag_hours == 0, "correlation"].iloc[0]),
                    )
                )
            curves.extend(
                profile.reset_index()
                .assign(city=city.slug, stage=stage, period=period)
                .to_dict("records")
            )
    save(fig, output, f"{city.slug}_alignment_diurnal")
    pd.DataFrame(lags).to_csv(output / f"{city.slug}_wind_lags.csv", index=False)
    return findings


def prepare_data(clock_shift_hours=-5.5):
    protocol = json.loads(Path("docs/results/PHASE3A2_PROTOCOL.json").read_text())
    with analysis_run(
        name="phase3a2-data", clock_shift_hours=clock_shift_hours, protocol=protocol
    ) as (run, output):
        fingerprint = measurement_fingerprint()
        geography, grids = geography_audit(output)
        coverage, networks, panels, lag_findings, nulls, manifests = [], [], [], [], [], []
        hyderabad = None
        with connection.cursor() as cursor:
            cursor.execute("SHOW timezone")
            database_timezone = cursor.fetchone()[0]
            cursor.execute(
                "SELECT table_name,data_type FROM information_schema.columns "
                "WHERE column_name='observed_at' "
                "AND table_name IN ('warehouse_reading','warehouse_weatherobservation')"
            )
            timestamp_types = cursor.fetchall()
        for city in City.objects.all():
            print(
                json.dumps(dict(event="diagnostic_data_city_started", city=city.slug)), flush=True
            )
            stations, inputs = station_hours(city, clock_shift_hours)
            weather = weather_frame(city)
            hourly, daily, city_coverage = snapshot_city(run, output, city, stations, weather)
            coverage.extend(city_coverage)
            stations.to_pickle(output / f"{city.slug}_station_hours.pkl")
            panel_stations, common = fixed_panel(stations)
            panel = join_weather(city_hours(panel_stations), weather) if common else pd.DataFrame()
            if not panel.empty:
                panel.to_pickle(output / f"{city.slug}_panel_hourly.pkl")
                panel_daily = aggregate_daily(panel, run.data_start, run.data_end)
                panel_daily.to_csv(output / f"{city.slug}_panel_raw_daily.csv", index=False)
                fig, axes = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
                for ax, (first, last) in zip(axes, [(2015, 2019), (2024, 2025)], strict=True):
                    for label, data in [("all stations", daily), ("fixed panel", panel_daily)]:
                        rows = data[pd.to_datetime(data.date).dt.year.between(first, last)].copy()
                        monthly = aggregate_monthly(rows, run.data_start, run.data_end)
                        ax.plot(pd.to_datetime(monthly.date), monthly.value, label=label)
                    ax.set_xlim(pd.Timestamp(f"{first}-01-01"), pd.Timestamp(f"{last}-12-31"))
                    ax.set_title(f"{city.name} {first}-{last}")
                    ax.set_ylabel("PM2.5 (ug/m3)")
                    ax.legend()
                save(fig, output, f"{city.slug}_station_panel")
            panels.append(dict(city=city.slug, common_sites=common, count=len(common)))
            for (year, source, site, name), group in stations.groupby(
                ["year", "source__slug", "external_id", "name"]
            ):
                networks.append(
                    dict(
                        city=city.slug,
                        year=int(year),
                        source=source,
                        site=site,
                        name=name,
                        hours=len(group),
                        first=group.observed_at.min().isoformat(),
                        last=group.observed_at.max().isoformat(),
                    )
                )
            eligible = [r["year"] for r in city_coverage if r["eligible"]]
            model_frame = hourly[
                hourly.observed_at.dt.tz_convert("Asia/Kolkata").dt.year.isin(eligible)
            ]
            lag_findings.extend(
                alignment_diagnostic(
                    city,
                    {
                        "legacy": analysis_dataframe(city.slug, 2),
                        "corrected IST"
                        if clock_shift_hours == -5.5
                        else "IST quarters": model_frame,
                    },
                    output,
                )
            )
            for period, group in weather.assign(period=period_labels(weather.observed_at)).groupby(
                "period"
            ):
                if period == "gap":
                    continue
                for variable in weather.columns.drop("observed_at"):
                    nulls.append(
                        dict(
                            city=city.slug,
                            period=period,
                            variable=variable,
                            hours=len(group),
                            nulls=int(group[variable].isna().sum()),
                        )
                    )
            manifests.extend(dict(city=city.slug, **m) for m in inputs)
            if city.slug == "hyderabad":
                hyderabad = hyderabad_audit(stations, daily)
                print(json.dumps(dict(event="hyderabad_sanity", **hyderabad)), flush=True)
            print(
                json.dumps(
                    dict(
                        event="diagnostic_data_city_finished",
                        city=city.slug,
                        eligible_years=eligible,
                        panel_sites=len(common),
                    )
                ),
                flush=True,
            )
        pd.DataFrame(coverage).to_csv(output / "analysis_coverage.csv", index=False)
        pd.DataFrame(networks).to_csv(output / "stations_by_year.csv", index=False)
        pd.DataFrame(lag_findings).to_csv(output / "alignment_summary.csv", index=False)
        pd.DataFrame(nulls).to_csv(output / "weather_nulls.csv", index=False)
        (output / "fixed_panels.json").write_text(json.dumps(panels, indent=2))
        (output / "inputs.json").write_text(json.dumps(manifests, indent=2))
        (output / "hyderabad_sanity.json").write_text(json.dumps(hyderabad, indent=2))
        after = measurement_fingerprint()
        if fingerprint != after:
            raise RuntimeError("Diagnostic reconstruction changed warehouse observations")
        run.results = dict(
            data_run=run.pk,
            geography_rows=len(geography),
            panels=panels,
            hyderabad=hyderabad,
            measurement_fingerprint=after,
            database_timezone=database_timezone,
            timestamp_types=timestamp_types,
            concentration_storage=(
                "Database timestamps are UTC timestamptz. Historical XKDR clocks are IST. "
                "Raw OpenCity UTC labels are retained as published; independently verified "
                "IST wall clocks are converted to UTC in this versioned analysis."
            ),
            weather_timezone="UTC request, utc_offset_seconds=0 validated",
            method_fix=(
                "Decode verified OpenCity IST wall clocks despite +0000 labels; existing "
                "four-quarter publisher-hour means are native IST-hour means after -5.5h. "
                "For literal UTC sensitivity runs, reconstruct bins across UTC-hour boundaries."
            ),
            source_clock_proof=(
                json.loads(Path("docs/results/PHASE3A2_CLOCK_PROOF.json").read_text())
                if clock_shift_hours == -5.5
                else None
            ),
        )
    return run.pk
