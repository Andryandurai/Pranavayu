import json
from datetime import timedelta

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import r2_score, root_mean_squared_error

from apps.warehouse.models import City, Pollutant

from .aggregation import aggregate_daily, analysis_dataframe, store_series
from .models import CityCoverage, CityMetric

# Grange et al. (2018), ACP 18, 6223–6239: https://doi.org/10.5194/acp-18-6223-2018
# rmweather defaults resample every covariate except date_unix:
# https://raw.githubusercontent.com/skgrange/rmweather/master/R/rmw_normalise.R
WEATHER = [
    "temperature_c",
    "relative_humidity",
    "wind_speed_ms",
    "wind_dir_deg",
    "surface_pressure_hpa",
    "precipitation_mm",
    "total_cloud_cover",
    "solar_radiation_wm2",
    "boundary_layer_height_m",
]


def design_matrix(frame):
    rows = frame.copy()
    time = pd.to_datetime(rows.observed_at, utc=True)
    local = time.dt.tz_convert("Asia/Kolkata")
    x = pd.DataFrame(
        {
            "date_trend_days": (time - pd.Timestamp("2015-01-01", tz="UTC")).dt.total_seconds()
            / 86400
        }
    )
    for feature in WEATHER:
        if feature == "boundary_layer_height_m" and rows[feature].notna().sum() == 0:
            continue
        x[feature] = rows[feature]
    for name, values, period in [
        ("day_of_year", local.dt.dayofyear, 365.25),
        ("hour", local.dt.hour, 24),
    ]:
        x[name + "_sin"] = np.sin(2 * np.pi * values / period)
        x[name + "_cos"] = np.cos(2 * np.pi * values / period)
    x["weekday"] = local.dt.weekday
    # Circular wind coordinates avoid a false discontinuity at north.
    x["wind_direction_sin"] = np.sin(np.deg2rad(x.pop("wind_dir_deg")))
    x["wind_direction_cos"] = np.cos(np.deg2rad(rows.wind_dir_deg))
    complete = x.notna().all(axis=1) & rows.value.notna()
    return rows.loc[complete].reset_index(drop=True), x.loc[complete].reset_index(drop=True).astype(
        np.float32
    )


def normalise(model, x, n_samples=300, seed=42):
    """Joint observed donor draws, holding only trend fixed; no missing-value imputation.

    Predictions are exactly constant between a fitted forest's trend split thresholds
    for a fixed donor. Evaluate one *observed* representative per such interval,
    then look up other observed targets. This avoids redundant predictions and
    creates no target for the 2020–2023 gap. A shared draw gives common random numbers.
    """
    if n_samples < 300:
        raise ValueError("Meteorological normalisation requires at least 300 draws")
    array = x.to_numpy(dtype=np.float32)
    thresholds = np.unique(
        np.concatenate(
            [tree.tree_.threshold[tree.tree_.feature == 0] for tree in model.estimators_]
        )
    )
    bins = np.searchsorted(thresholds, array[:, 0], side="left")
    _, first, inverse = np.unique(bins, return_index=True, return_inverse=True)
    rng = np.random.default_rng(seed)
    donors = array[rng.integers(0, len(array), size=n_samples)].copy()
    predictions = np.empty((len(first), n_samples))
    for offset in range(0, len(first), 64):
        dates = array[first[offset : offset + 64], 0]
        scenarios = np.tile(donors, (len(dates), 1))
        scenarios[:, 0] = np.repeat(dates, n_samples)
        predictions[offset : offset + len(dates)] = model.predict(scenarios).reshape(
            len(dates), n_samples
        )
    return (
        predictions,
        inverse,
        {
            "draws": n_samples,
            "seed": seed,
            "trend_intervals": len(first),
            "targets": len(x),
            "sampler": "Common joint observed complete-case donor rows; trend held fixed",
        },
    )


def deweather_series(rows, predictions, inverse, start, end):
    hour = rows[["observed_at"]].copy()
    hour["value"] = predictions.mean(axis=1)[inverse]
    daily = aggregate_daily(hour, start, end)
    daily_samples = {}
    local = pd.to_datetime(rows.observed_at, utc=True).dt.tz_convert("Asia/Kolkata").dt.date
    for day, indices in pd.Series(np.arange(len(rows))).groupby(local):
        if len(indices) >= 18:
            daily_samples[day] = predictions[inverse[indices.to_numpy()]].mean(axis=0)
    daily["sampling_se"] = [
        float(daily_samples[d].std(ddof=1) / np.sqrt(predictions.shape[1]))
        if d in daily_samples
        else None
        for d in daily.date
    ]
    # Do not manufacture a modelled row for unobserved/gap days. Missing days
    # stay in coverage denominators, but only actual model targets are exported.
    daily = daily[daily.date.isin(set(local))].copy()
    monthly = []
    for month, group in daily.groupby(pd.to_datetime(daily.date).dt.to_period("M")):
        first = month.start_time.date()
        expected = (min(end, month.end_time.date()) - max(start, first)).days + 1
        valid = group.dropna(subset=["value"])
        enough = len(valid) / expected >= 0.75
        samples = np.stack([daily_samples[d] for d in valid.date]).mean(axis=0) if enough else None
        monthly.append(
            {
                "date": first,
                "value": float(samples.mean()) if enough else None,
                "valid_count": len(valid),
                "expected_count": expected,
                "sampling_se": float(samples.std(ddof=1) / np.sqrt(len(samples)))
                if enough
                else None,
            }
        )
    return daily, pd.DataFrame(
        monthly, columns=["date", "value", "valid_count", "expected_count", "sampling_se"]
    )


def fit_city(frame, n_trees=100, n_samples=300, seed=42):
    rows, x = design_matrix(frame)
    if len(rows) < 240:
        raise ValueError("Insufficient complete-case hours for a blocked model")
    order = np.argsort(rows.observed_at.to_numpy())
    rows = rows.iloc[order].reset_index(drop=True)
    x = x.iloc[order].reset_index(drop=True)
    cutoff = rows.observed_at.iloc[int(0.8 * len(rows))]
    train = rows.observed_at < cutoff - timedelta(days=7)
    test = rows.observed_at >= cutoff
    if train.sum() < 120 or test.sum() < 48:
        raise ValueError("Insufficient time-blocked train/test hours")
    parameters = dict(
        n_estimators=n_trees,
        max_depth=12,
        min_samples_leaf=12,
        max_features=0.7,
        random_state=seed,
        n_jobs=1,
    )
    validation = RandomForestRegressor(**parameters).fit(
        x.loc[train].to_numpy(), rows.loc[train, "value"]
    )
    actual = rows.loc[test, "value"].to_numpy()
    prediction = validation.predict(x.loc[test].to_numpy())
    rmse = float(root_mean_squared_error(actual, prediction))
    bias = float((prediction - actual).mean())
    score = float(r2_score(actual, prediction))
    mean = float(actual.mean())
    importance = permutation_importance(
        validation,
        x.loc[test].to_numpy(),
        actual,
        n_repeats=5,
        random_state=seed,
        n_jobs=1,
        max_samples=min(3000, len(actual)),
    )
    result = {
        "r2": score,
        "rmse": rmse,
        "bias": bias,
        "holdout_mean": mean,
        "train_hours": int(train.sum()),
        "test_hours": int(test.sum()),
        "complete_case_hours": len(rows),
        "input_hours": len(frame),
        "hours_removed_missing_weather": len(frame) - len(rows),
        "train_end": rows.loc[train, "observed_at"].max().isoformat(),
        "holdout_start": cutoff.isoformat(),
        "holdout_end": rows.loc[test, "observed_at"].max().isoformat(),
        "purge_days": 7,
        "parameters": parameters,
        "features": list(x.columns),
        "permutation_importance": {
            key: {"mean_delta_r2": float(avg), "std": float(sd)}
            for key, avg, sd in zip(
                x.columns, importance.importances_mean, importance.importances_std, strict=True
            )
        },
        "reliable_screen": bool(
            score >= 0.5
            and rmse <= 0.5 * mean
            and abs(bias) <= 0.1 * mean
            and train.sum() >= 2000
            and test.sum() >= 1000
        ),
    }
    model = RandomForestRegressor(**parameters).fit(x.to_numpy(), rows.value)
    preds, inverse, normalisation = normalise(model, x, n_samples, seed)
    result["normalisation"] = normalisation
    return rows, model, preds, inverse, result


def run_deweather(run, output, n_trees=100, n_samples=300, seed=42):
    results = []
    pollutant = Pollutant.objects.get(code="pm25")
    for city in City.objects.all():
        years = set(
            CityCoverage.objects.filter(
                run=run, city=city, pollutant=pollutant, eligible=True
            ).values_list("year", flat=True)
        )
        frame = analysis_dataframe(city.slug, run)
        frame = frame[frame.observed_at.dt.tz_convert("Asia/Kolkata").dt.year.isin(years)]
        print(
            json.dumps({"event": "model_started", "city": city.slug, "hours": len(frame)}),
            flush=True,
        )
        if frame.empty:
            result = {
                "city": city.slug,
                "status": "unavailable",
                "reason": "No eligible observed city-year",
            }
        else:
            rows, model, preds, inverse, performance = fit_city(frame, n_trees, n_samples, seed)
            daily, monthly = deweather_series(rows, preds, inverse, run.data_start, run.data_end)
            store_series(run, city, pollutant, daily, "deweathered", "daily")
            store_series(run, city, pollutant, monthly, "deweathered", "monthly")
            daily.to_csv(output / f"{city.slug}_deweathered_daily.csv", index=False)
            monthly.to_csv(output / f"{city.slug}_deweathered_monthly.csv", index=False)
            joblib.dump(model, output / f"{city.slug}_random_forest.joblib", compress=3)
            result = {
                "city": city.slug,
                "status": "success",
                "eligible_years": sorted(years),
                **performance,
            }
        CityMetric.objects.create(run=run, city=city, name="deweathering", result=result)
        (output / f"{city.slug}_model.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        results.append(result)
        print(
            json.dumps(
                {
                    "event": "model_finished",
                    **{
                        k: v
                        for k, v in result.items()
                        if k in {"city", "status", "r2", "rmse", "bias", "reliable_screen"}
                    },
                }
            ),
            flush=True,
        )
    pd.DataFrame(
        [{k: v for k, v in r.items() if not isinstance(v, (dict, list))} for r in results]
    ).to_csv(output / "deweathering_performance.csv", index=False)
    return results
