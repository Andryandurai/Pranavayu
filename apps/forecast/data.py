"""Raw targets, issue-time features and expanding-origin partitions."""

import hashlib
import json
from datetime import timedelta

import holidays
import numpy as np
import pandas as pd
from django.conf import settings

from apps.analytics.aggregation import aggregate_daily
from apps.analytics.descriptive import DIWALI, season

from .models import ForecastWeather
from .weather import issue_end

PM_FEATURES = [
    "pm_t",
    "pm_tminus1",
    "pm_tminus2",
    "pm_tminus7",
    "pm_mean3",
    "pm_mean7",
    "pm_night_mean",
    "pm_day_max",
]
WEATHER_FEATURES = [
    "temperature_c",
    "relative_humidity",
    "wind_speed_ms",
    "wind_sin",
    "wind_cos",
    "precipitation_mm",
    "total_cloud_cover",
    "surface_pressure_hpa",
]
CALENDAR_FEATURES = ["weekday", "month", "holiday", "diwali_window", "season", "doy_sin", "doy_cos"]
FEATURES = PM_FEATURES + WEATHER_FEATURES + CALENDAR_FEATURES


def raw_daily(hourly, start="2024-01-01", end="2025-12-31"):
    daily = aggregate_daily(hourly, pd.Timestamp(start).date(), pd.Timestamp(end).date())
    daily.index = pd.to_datetime(daily.pop("date"))
    local = pd.to_datetime(hourly.observed_at, utc=True).dt.tz_convert("Asia/Kolkata")
    work = hourly.assign(date=local.dt.tz_localize(None).dt.normalize(), hour=local.dt.hour)
    daily["night_mean"] = work[(work.hour < 6) | (work.hour >= 20)].groupby("date").value.mean()
    daily["day_max"] = work.groupby("date").value.max()
    for name, lag in zip(PM_FEATURES[:4], (0, 1, 2, 7), strict=True):
        daily[name] = daily.value.shift(lag)
    daily["pm_mean3"] = daily.value.rolling(3, min_periods=3).mean()
    daily["pm_mean7"] = daily.value.rolling(7, min_periods=7).mean()
    daily["pm_night_mean"] = daily.night_mean
    daily["pm_day_max"] = daily.day_max
    return daily


def load_hourly(slug):
    suffix = "panel_hourly" if slug == "bengaluru" else "hourly"
    path = settings.BASE_DIR / "data" / "results" / "8" / f"{slug}_{suffix}.pkl"
    frame = pd.read_pickle(path)
    dates = pd.to_datetime(frame.observed_at, utc=True).dt.tz_convert("Asia/Kolkata")
    frame = frame[(dates.dt.year >= 2024) & (dates.dt.year <= 2025)].copy()
    return frame, {
        "path": str(path.relative_to(settings.BASE_DIR)),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "data_run": 8,
        "cohort": "fixed_panel" if slug == "bengaluru" else "all_stations",
        "normalised_input": False,
    }


def calendar_features(target_dates):
    dates = pd.DatetimeIndex(target_dates)
    india = holidays.India(years=sorted(set(dates.year)))
    result = pd.DataFrame(index=dates)
    result["weekday"] = dates.dayofweek
    result["month"] = dates.month
    result["holiday"] = [int(d.date() in india) for d in dates]
    result["diwali_window"] = [
        int(d.year in DIWALI and abs((d.date() - DIWALI[d.year]).days) <= 3) for d in dates
    ]
    result["season"] = [
        {"winter": 0, "pre_monsoon": 1, "monsoon": 2, "post_monsoon": 3}[season(d.month)]
        for d in dates
    ]
    result["doy_sin"] = np.sin(2 * np.pi * dates.dayofyear / 365.25)
    result["doy_cos"] = np.cos(2 * np.pi * dates.dayofyear / 365.25)
    return result


def observed_daily_weather(hourly):
    dates = (
        pd.to_datetime(hourly.observed_at, utc=True)
        .dt.tz_convert("Asia/Kolkata")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    frame = hourly.copy()
    radians = np.deg2rad(frame.wind_dir_deg)
    frame["wind_sin"] = np.sin(radians)
    frame["wind_cos"] = np.cos(radians)
    frame["date"] = dates
    weather = frame.groupby("date")[WEATHER_FEATURES].mean()
    weather["precipitation_mm"] = frame.groupby("date").precipitation_mm.sum(min_count=18)
    return weather


def make_features(daily, weather_records, horizon, observed=None):
    """Forecast valid times are future; feature availability timestamps are past."""
    rows = daily[PM_FEATURES].copy()
    rows["issued_for_date"] = rows.index
    rows["target_date"] = pd.DatetimeIndex(rows.index.to_numpy() + np.timedelta64(horizon, "D"))
    rows["y"] = daily.value.reindex(rows.target_date).to_numpy()
    calendar = calendar_features(rows.target_date)
    for col in CALENDAR_FEATURES:
        rows[col] = calendar[col].to_numpy()
    weather = pd.DataFrame(weather_records)
    if weather.empty:
        return pd.DataFrame(columns=[*FEATURES, "issued_for_date", "target_date", "y"])
    weather["issued_for_date"] = pd.to_datetime(weather.issued_for_date)
    weather = weather.set_index("issued_for_date")
    for col in WEATHER_FEATURES:
        rows[col] = pd.Series(
            {idx: r.get(col) for idx, r in zip(weather.index, weather.features, strict=True)}
        ).reindex(rows.index)
    rows["weather_available_by"] = pd.to_datetime(weather.available_by, utc=True).reindex(
        rows.index
    )
    rows["weather_asset"] = weather.asset_id.reindex(rows.index)
    rows["weather_kind"] = "archived_forecast"
    cutoffs = pd.Series([issue_end(day.date()) for day in rows.index], index=rows.index)
    if (rows.weather_available_by > cutoffs).any():
        raise ValueError("Forecast weather availability exceeds its issue cutoff")
    if observed is not None:
        for col in WEATHER_FEATURES:
            rows[col] = observed[col].reindex(rows.target_date).to_numpy()
        rows["weather_kind"] = "perfect_prognosis_observed"
    for lag in range(7):
        rows[f"seq_{lag}"] = daily.value.shift(lag)
    return rows.dropna(subset=[*FEATURES, *[f"seq_{i}" for i in range(7)]])


def city_dataset(slug, horizon):
    hourly, provenance = load_hourly(slug)
    daily = raw_daily(hourly)
    records = list(
        ForecastWeather.objects.filter(city__slug=slug, horizon=horizon, mode="archive")
        .order_by("issued_for_date")
        .values("issued_for_date", "available_by", "asset_id", "features")
    )
    real = make_features(daily, records, horizon)
    ideal = make_features(daily, records, horizon, observed_daily_weather(hourly))
    shared = real.index.intersection(ideal.index)
    return daily, real.loc[shared], ideal.loc[shared], provenance


def feature_provenance(row, horizon):
    end = issue_end(row.issued_for_date.date())
    available = pd.Timestamp(row.weather_available_by)
    if row.weather_kind not in {"archived_forecast", "live_forecast"} or available > end:
        raise ValueError("Future or observed weather cannot enter an issued forecast")
    return {
        "persistence_value": float(row.pm_t),
        "issue_end_utc": end.isoformat(),
        "concentration_latest_available_at": end.isoformat(),
        "weather_available_by": available.isoformat(),
        "weather_asset_id": int(row.weather_asset),
        "weather_kind": row.weather_kind,
        "weather_target_date": str(row.target_date.date()),
        "lead_days": horizon + 1 if row.weather_kind == "archived_forecast" else None,
        "feature_availability": {
            name: (available.isoformat() if name in WEATHER_FEATURES else end.isoformat())
            for name in FEATURES
        },
        "concentration_publication_assumption": (
            "day-t readings available at issue-end; historical release logs absent"
        ),
    }


def rolling_origins(rows, latest_target):
    latest = pd.Timestamp(latest_target)
    first = (latest.to_period("M") - 5).start_time
    scored = rows[(rows.target_date >= first) & (rows.target_date <= latest) & rows.y.notna()]
    for month, test in scored.groupby(scored.issued_for_date.dt.to_period("M")):
        origin = test.issued_for_date.min()
        train = rows[(rows.target_date <= origin) & rows.y.notna()]
        if len(train) < 180:
            raise ValueError(f"Insufficient expanding training support at {origin}")
        yield str(month), origin, train, test


def training_segments(train, origin):
    calibration_start = pd.Timestamp(pd.Timestamp(origin).date() - timedelta(days=60))
    tuning_start = pd.Timestamp(calibration_start.date() - timedelta(days=60))
    fit = train[train.target_date < tuning_start]
    tune = train[(train.issued_for_date >= tuning_start) & (train.target_date < calibration_start)]
    final_fit = train[train.target_date < calibration_start]
    calibration = train[
        (train.issued_for_date >= calibration_start) & (train.target_date <= origin)
    ]
    if min(len(fit), len(tune), len(calibration)) < 25:
        raise ValueError("Insufficient purged fit/tune/calibration support")
    return fit, tune, final_fit, calibration


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, default=str, allow_nan=False), encoding="utf-8")
