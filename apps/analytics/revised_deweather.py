"""Prespecified Phase 3A2 model comparisons and observed-only common-reference outputs."""

import gc
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from threadpoolctl import threadpool_limits

from .aggregation import aggregate_daily, aggregate_monthly, analysis_dataframe, store_series
from .descriptive import era_difference
from .lifecycle import analysis_run
from .model_diagnostics import (
    evaluate,
    features,
    forest,
    period_labels,
    pooled_normalise,
    readiness,
    residual_tables,
    scores,
    target_rows,
    weather_daily,
)
from .models import AnalysisRun, CityCoverage, CityMetric


def json_result(result):
    return {
        key: value
        for key, value in result.items()
        if key not in {"rows", "prediction", "daily_rows"}
    }


def eligible_frame(frame, coverage):
    years = {r["year"] for r in coverage if r["eligible"]}
    return frame[frame.observed_at.dt.tz_convert("Asia/Kolkata").dt.year.isin(years)].copy()


def panel_coverage(frame, start, end):
    daily = aggregate_daily(frame, start, end)
    result = []
    for year, group in daily.groupby(pd.to_datetime(daily.date).dt.year):
        result.append(
            dict(
                year=int(year),
                eligible=group.value.notna().sum() / len(group) >= 0.75
                and group.valid_count.sum() / (24 * len(group)) >= 0.75,
            )
        )
    return result


def trial(city, frame, weather, config, output):
    print(json.dumps(dict(event="variant_started", city=city, variant=config["name"])), flush=True)
    result = evaluate(frame, weather, config)
    result["daily_rows"].to_csv(output / f"{city}_{config['name']}_oof_daily.csv", index=False)
    (output / f"{city}_{config['name']}_cv.json").write_text(
        json.dumps(json_result(result), indent=2)
    )
    print(
        json.dumps(
            dict(
                event="variant_finished",
                city=city,
                variant=config["name"],
                daily_r2=result["daily"]["r2"],
                native_r2=result["native"]["r2"],
            )
        ),
        flush=True,
    )
    return result


def select_variant(trials):
    common = set(trials[0]["daily_rows"].date)
    for result in trials[1:]:
        common &= set(result["daily_rows"].date)
    if not common:
        raise ValueError("No common valid daily targets across prespecified variants")
    comparisons = []
    for result in trials:
        daily = result["daily_rows"]
        daily = daily[daily.date.isin(common)]
        metrics = {
            period: scores(group.value, group.prediction)
            for period, group in daily.groupby("period")
        }
        quality = float(np.mean([m["r2"] for m in metrics.values()]))
        comparisons.append(
            dict(
                variant=result["config"]["name"],
                common_days=len(daily),
                selection_r2=quality,
                periods=metrics,
            )
        )
    index = max(range(len(comparisons)), key=lambda i: (comparisons[i]["selection_r2"], -i))
    return trials[index], comparisons


def historical_normalisation(frame, weather, config, output, prefix):
    rows, x = features(target_rows(frame, weather, config["target"]), config)
    reference = weather[period_labels(weather.observed_at) != "gap"].copy()
    if config["target"] == "daily":
        reference = weather_daily(reference)
    _, reference_x = features(reference, config)
    periods = period_labels(rows.observed_at)
    values = np.empty(len(rows))
    daily_draws = {}
    model_metadata = []
    groups = sorted(set(periods)) if config["periods"] == "separate" else [None]
    for group in groups:
        mask = np.ones(len(rows), dtype=bool) if group is None else periods == group
        model = forest().fit(x.loc[mask].to_numpy(), rows.loc[mask, "value"])
        mean, error, samples, inverse = pooled_normalise(
            model, x.loc[mask], reference_x, return_draws=True
        )
        indices = np.flatnonzero(mask)
        values[indices] = mean
        name = group or "pooled"
        joblib.dump(model, output / f"{prefix}_{name}_forest.joblib", compress=3)
        model_metadata.append(
            dict(
                period=name,
                training_rows=int(mask.sum()),
                parameters=model.get_params(),
                reference_rows=len(reference_x),
                reference_weather_periods=["2015-2019", "2024-2025"],
                reference_draws=300,
                seed=42,
                features=list(x.columns),
                importance=dict(
                    zip(x.columns, map(float, model.feature_importances_), strict=True)
                ),
            )
        )
        local = (
            pd.to_datetime(rows.loc[mask, "observed_at"], utc=True)
            .dt.tz_convert("Asia/Kolkata")
            .dt.date.reset_index(drop=True)
        )
        for day, position in pd.Series(np.arange(len(local))).groupby(local):
            if config["target"] == "daily" or len(position) >= 18:
                daily_draws[day] = samples[inverse[position.to_numpy()]].mean(axis=0)
    normalised = rows[["observed_at"]].copy()
    normalised["value"] = values
    if config["target"] == "hourly":
        daily = aggregate_daily(
            normalised,
            frame.observed_at.dt.tz_convert("Asia/Kolkata").dt.date.min(),
            frame.observed_at.dt.tz_convert("Asia/Kolkata").dt.date.max(),
        )
        daily = daily[
            daily.date.isin(
                set(
                    pd.to_datetime(rows.observed_at, utc=True).dt.tz_convert("Asia/Kolkata").dt.date
                )
            )
        ]
    else:
        daily = pd.DataFrame(
            dict(
                date=pd.to_datetime(rows.observed_at, utc=True)
                .dt.tz_convert("Asia/Kolkata")
                .dt.date,
                value=values,
                valid_count=rows.valid_count.to_numpy(),
                expected_count=24,
            )
        )
    daily["sampling_se"] = [
        float(daily_draws[day].std(ddof=1) / np.sqrt(300)) if day in daily_draws else None
        for day in daily.date
    ]
    # Missing days still count in monthly denominators. Never store a model row in the gap.
    first = pd.Timestamp(min(daily.date)).to_period("M").start_time.date()
    last = pd.Timestamp(max(daily.date)).to_period("M").end_time.date()
    calendar = pd.date_range(first, last, freq="D").date
    complete = daily.set_index("date").reindex(calendar).rename_axis("date").reset_index()
    monthly = aggregate_monthly(complete, min(calendar), max(calendar))
    observed_months = set(pd.to_datetime(daily.date).dt.to_period("M"))
    monthly = monthly[pd.to_datetime(monthly.date).dt.to_period("M").isin(observed_months)].copy()
    monthly["sampling_se"] = None
    for i, row in monthly.iterrows():
        if row.value is not None and pd.notna(row.value):
            days = [
                day
                for day in daily_draws
                if pd.Timestamp(day).to_period("M") == pd.Timestamp(row.date).to_period("M")
            ]
            draws = np.stack([daily_draws[d] for d in days]).mean(axis=0)
            monthly.loc[i, "sampling_se"] = float(draws.std(ddof=1) / np.sqrt(300))
    daily.to_csv(output / f"{prefix}_deweathered_daily.csv", index=False)
    monthly.to_csv(output / f"{prefix}_deweathered_monthly.csv", index=False)
    return daily, monthly, model_metadata


def difference_intervals(raw, normalised, oof):
    raw = raw.dropna(subset=["value"])
    result = {"raw": era_difference(raw)}
    normalised = normalised.dropna(subset=["value"])
    # Centred out-of-fold residuals keep a no-trend forest's constant period level
    # from misleadingly implying zero conditional variability in a block bootstrap.
    rows = normalised.merge(
        oof[["date", "value", "prediction", "period"]], on="date", suffixes=("", "_actual")
    )
    rows["residual"] = rows.value_actual - rows.prediction
    rows["residual"] -= rows.groupby("period").residual.transform("mean")
    adjusted = rows[["date", "value"]].copy()
    adjusted["value"] += rows.residual
    conditional = era_difference(adjusted)
    point = era_difference(normalised, samples=1)
    if point["status"] == "descriptive":
        conditional.update({k: point[k] for k in ["baseline_mean", "recent_mean", "difference"]})
        conditional["uncertainty"] = (
            "Conditional centred week-CV residual and year/seven-day block bootstrap; "
            "excludes refit, reference-weather and network uncertainty"
        )
    result["normalised"] = conditional
    return result


def clone_snapshot(data_run, run):
    from django.db import connection

    with connection.cursor() as cursor:
        for table, fields in [
            (
                "analytics_cityhourly",
                "city_id,pollutant_id,observed_at,value,station_count,weather",
            ),
            (
                "analytics_citycoverage",
                "city_id,pollutant_id,year,hours_present,hours_expected,valid_days,expected_days,valid_months,eligible",
            ),
            (
                "analytics_cityseries",
                "city_id,pollutant_id,kind,frequency,date,value,valid_count,expected_count,sampling_se",
            ),
        ]:
            cursor.execute(
                f"INSERT INTO {table}(run_id,{fields}) "
                f"SELECT %s,{fields} FROM {table} WHERE run_id=%s",
                [run.pk, data_run.pk],
            )


def run_revised(data_run_id):
    from apps.warehouse.models import City, Pollutant

    protocol_path = Path("docs/results/PHASE3A2_PROTOCOL.json")
    protocol = json.loads(protocol_path.read_text())
    data_run = AnalysisRun.objects.get(pk=data_run_id, status="success", name="phase3a2-data")
    inputs = Path("data/results") / str(data_run_id)
    with analysis_run(
        name="phase3a2",
        protocol=protocol,
        protocol_sha256=hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
        data_run=data_run_id,
        baseline_run=2,
    ) as (run, output):
        clone_snapshot(data_run, run)
        summary, comparisons, original, changes = [], [], [], []
        pm = Pollutant.objects.get(code="pm25")
        for city in City.objects.all():
            print(json.dumps(dict(event="revised_city_started", city=city.slug)), flush=True)
            weather = pd.read_pickle(inputs / f"{city.slug}_weather.pkl")
            full = pd.read_pickle(inputs / f"{city.slug}_hourly.pkl")
            coverage = list(
                CityCoverage.objects.filter(run=run, city=city).values("year", "eligible")
            )
            frame = eligible_frame(full, coverage)
            # Diagnose the original predictor on original data, varying only validation.
            legacy = analysis_dataframe(city.slug, 2)
            years = CityCoverage.objects.filter(run_id=2, city=city, eligible=True).values_list(
                "year", flat=True
            )
            legacy = legacy[
                legacy.observed_at.dt.tz_convert("Asia/Kolkata").dt.year.isin(set(years))
            ]
            config = dict(name="original", target="hourly", trend=True, periods="pooled", blh=True)
            with threadpool_limits(limits=1):
                d4 = Parallel(n_jobs=2, prefer="threads")(
                    delayed(evaluate)(legacy, weather, config, scheme=scheme, original=True)
                    for scheme in ["random", "weeks", "transfer"]
                )
                trials = Parallel(n_jobs=2, prefer="threads")(
                    delayed(trial)(city.slug, frame, weather, variant, output)
                    for variant in protocol["variants"]
                )
            original.extend(dict(city=city.slug, **json_result(r)) for r in d4)
            selected, choice = select_variant(trials)
            comparisons.extend(dict(city=city.slug, **r) for r in choice)
            config = selected["config"]
            gate = readiness(selected["daily_rows"], protocol["criteria"])
            with threadpool_limits(limits=1):
                random, transfer = Parallel(n_jobs=2, prefer="threads")(
                    delayed(evaluate)(frame, weather, config, scheme=scheme)
                    for scheme in ["random", "transfer"]
                )
                daily, monthly, models = historical_normalisation(
                    frame, weather, config, output, city.slug
                )
            store_series(run, city, pm, daily, "deweathered", "daily")
            store_series(run, city, pm, monthly, "deweathered", "monthly")
            residual = residual_tables(selected["daily_rows"])
            for label, table in residual.items():
                pd.DataFrame(table).to_csv(
                    output / f"{city.slug}_residual_{label}.csv", index=False
                )
            raw = aggregate_daily(frame, run.data_start, run.data_end).dropna(subset=["value"])
            difference = difference_intervals(raw, daily, selected["daily_rows"])
            panel_path = inputs / f"{city.slug}_panel_hourly.pkl"
            panel_result = {
                "status": "unavailable",
                "reason": "No matched CPCB site IDs in both periods",
            }
            if panel_path.exists():
                panel = pd.read_pickle(panel_path)
                panel = eligible_frame(panel, panel_coverage(panel, run.data_start, run.data_end))
                if len(set(period_labels(panel.observed_at))) == 2:
                    with threadpool_limits(limits=1):
                        panel_cv = evaluate(panel, weather, config)
                        p_daily, p_monthly, p_models = historical_normalisation(
                            panel, weather, config, output, f"{city.slug}_panel"
                        )
                    p_raw = aggregate_daily(panel, run.data_start, run.data_end).dropna(
                        subset=["value"]
                    )
                    panel_result = {
                        "status": "available",
                        "differences": difference_intervals(p_raw, p_daily, panel_cv["daily_rows"]),
                        "readiness": readiness(panel_cv["daily_rows"], protocol["criteria"]),
                        "models": p_models,
                    }
                else:
                    panel_result = {
                        "status": "unavailable",
                        "reason": "Matched stations lack eligible years in both periods",
                    }
            result = dict(
                city=city.slug,
                selected_design=config,
                readiness=gate,
                random=json_result(random),
                week_cv=json_result(selected),
                transfer=json_result(transfer),
                models=models,
                differences=difference,
                fixed_panel=panel_result,
            )
            summary.append(result)
            changes.append(dict(city=city.slug, series="all_raw", **difference["raw"]))
            changes.append(
                dict(city=city.slug, series="all_normalised", **difference["normalised"])
            )
            if panel_result["status"] == "available":
                for label, value in panel_result["differences"].items():
                    changes.append(dict(city=city.slug, series=f"panel_{label}", **value))
            CityMetric.objects.create(
                run=run, city=city, name="deweathering_diagnostics", result=result
            )
            (output / f"{city.slug}_revised_model.json").write_text(json.dumps(result, indent=2))
            print(
                json.dumps(
                    dict(
                        event="revised_city_finished",
                        city=city.slug,
                        design=config["name"],
                        passed=gate["passed"],
                        daily_r2=selected["daily"]["r2"],
                    )
                ),
                flush=True,
            )
            del trials, d4, selected, frame, legacy, full, weather
            gc.collect()
        (output / "D4_original_validation.json").write_text(json.dumps(original, indent=2))
        (output / "D5_comparisons.json").write_text(json.dumps(comparisons, indent=2))
        pd.DataFrame(changes).to_csv(output / "old_recent_differences.csv", index=False)
        (output / "readiness.json").write_text(json.dumps(summary, indent=2))
        run.results = dict(
            data_run=data_run_id,
            models=summary,
            passed_cities=[r["city"] for r in summary if r["readiness"]["passed"]],
            report="docs/results/PHASE3A2.md",
        )
    return run.pk
