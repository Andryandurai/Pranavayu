import os
from datetime import timedelta

import joblib
import numpy as np
import pandas as pd
from django.conf import settings
from django.db import connection
from django.utils import timezone

from apps.ingest.sources.openaq import OpenAQSource
from apps.warehouse.models import City

from .data import load_hourly, make_features, raw_daily
from .estimators import predict
from .explain import top_drivers
from .models import ForecastModelVersion, ForecastWeather
from .pipeline import save_forecasts
from .weather import ForecastWeatherSource, issue_end


def operational_hourly(city, day):
    """Only readings whose ingestion finished before this issue cutoff."""
    first = pd.Timestamp(day - timedelta(days=9), tz="Asia/Kolkata").to_pydatetime()
    cutoff = issue_end(day).to_pydatetime()
    panel = None
    if city.slug == "bengaluru":
        import json

        rows = json.loads(
            (settings.BASE_DIR / "data" / "results" / "8" / "fixed_panels.json").read_text()
        )
        panel = next(r["common_sites"] for r in rows if r["city"] == city.slug)
    with connection.cursor() as cursor:
        cursor.execute(
            """WITH station_hours AS (
            SELECT s.id, date_trunc('hour',r.observed_at AT TIME ZONE 'Asia/Kolkata')
                AT TIME ZONE 'Asia/Kolkata' AS observed_at, avg(r.value) AS value
            FROM warehouse_reading r JOIN warehouse_station s ON s.id=r.station_id
            JOIN ingest_ingestionrun ir ON ir.id=r.ingestion_run_id
            JOIN warehouse_pollutant p ON p.id=r.pollutant_id
            LEFT JOIN analytics_stationeligibility e ON e.station_id=s.id
            WHERE s.city_id=%s AND p.code='pm25' AND r.quality_flag='ok'
                AND r.value IS NOT NULL AND r.observed_at >= %s AND r.observed_at <= %s
                AND ir.finished_at <= %s AND coalesce(e.excluded_from_city,false)=false
                AND (%s::text[] IS NULL OR s.external_id=ANY(%s::text[]))
            GROUP BY s.id,2
        ) SELECT observed_at,avg(value) AS value,count(*) AS station_count
          FROM station_hours GROUP BY observed_at ORDER BY observed_at""",
            [city.pk, first, cutoff, cutoff, panel, panel],
        )
        return pd.DataFrame(cursor.fetchall(), columns=["observed_at", "value", "station_count"])


def select_issue_mode(key_present, fresh_day, completed_day, replay_date=None):
    if replay_date is not None:
        return "replay", pd.Timestamp(replay_date).date()
    if key_present and fresh_day == completed_day:
        return "live", completed_day
    return "replay", fresh_day


def observed_history(daily, rows, horizon):
    """Keep every measured label even when that day's exogenous row is missing."""
    history = rows.reindex(daily.index).copy()
    targets = pd.DatetimeIndex(daily.index.to_numpy() + np.timedelta64(horizon, "D"))
    history["y"] = daily.value.reindex(targets).to_numpy()
    return history


def operational_intervals(bundle, rows, history):
    """Use frozen calibration radii; current live history cannot rewrite old errors."""
    selection = bundle["selection"]
    q80, q95 = selection["radius80"], selection["radius95"]
    point = predict(bundle["model"], rows, history)
    result = {
        "prediction": point,
        "lower80": np.maximum(0, point - q80),
        "upper80": point + q80,
        "lower95": np.maximum(0, point - q95),
        "upper95": point + q95,
    }
    # Quantile trees depend only on their saved calibration feature rows, not state.
    calibration = bundle["calibration"]
    for lower, upper, alpha in [(0.1, 0.9, 0.2), (0.025, 0.975, 0.05)]:
        cl = bundle["quantiles"][str(lower)].predict(calibration)
        cu = bundle["quantiles"][str(upper)].predict(calibration)
        errors = np.maximum(
            np.minimum(cl, cu) - calibration.y.to_numpy(),
            calibration.y.to_numpy() - np.maximum(cl, cu),
        )
        rank = int(np.ceil((len(errors) + 1) * (1 - alpha)))
        adjustment = max(0, float(np.sort(errors)[rank - 1]))
        lo = bundle["quantiles"][str(lower)].predict(rows)
        hi = bundle["quantiles"][str(upper)].predict(rows)
        label = "80" if alpha == 0.2 else "95"
        result[f"quantile_lower{label}"] = np.maximum(0, np.minimum(lo, hi) - adjustment)
        result[f"quantile_upper{label}"] = np.maximum(lo, hi) + adjustment
    result["quantile_lower95"] = np.minimum(result["quantile_lower95"], result["quantile_lower80"])
    result["quantile_upper95"] = np.maximum(result["quantile_upper95"], result["quantile_upper80"])
    return result, {"radius80": q80, "radius95": q95, "calibration_n": len(calibration)}


def issue_feature_rows(city, daily, mode):
    result = {}
    for horizon in (1, 2, 3):
        weather = ForecastWeather.objects.filter(city=city, horizon=horizon)
        if mode == "replay":
            weather = weather.filter(mode="archive")
        by_issue = {
            r["issued_for_date"]: r
            for r in weather.order_by("issued_for_date", "mode").values(
                "issued_for_date", "available_by", "asset_id", "features"
            )
        }
        result[horizon] = make_features(daily, list(by_issue.values()), horizon)
    return result


def issue_forecasts(replay_date=None, cities=None):
    results = []
    completed = timezone.localdate() - timedelta(days=1)
    key_present = bool(os.environ.get("OPENAQ_API_KEY"))
    for city in City.objects.filter(slug__in=cities or settings.FORECAST_CITIES).order_by("slug"):
        hourly, provenance = load_hourly(city.slug)
        daily = raw_daily(hourly)
        latest = daily[daily.value.notna()].index.max().date()
        live = (
            operational_hourly(city, completed)
            if key_present and replay_date is None
            else pd.DataFrame()
        )
        if not live.empty:
            live_daily = raw_daily(live, str(completed - timedelta(days=9)), str(completed))
            fresh = (
                completed if pd.notna(live_daily.loc[pd.Timestamp(completed), "value"]) else latest
            )
        else:
            fresh = latest
        mode, issued = select_issue_mode(key_present, fresh, completed, replay_date)
        if mode == "live":
            combined = pd.concat([hourly, live], ignore_index=True)
            combined = combined.drop_duplicates("observed_at", keep="last")
            daily = raw_daily(combined, "2024-01-01", str(completed))
        feature_rows = issue_feature_rows(city, daily, mode)
        fallback_reason = ""
        if mode == "live" and any(
            pd.Timestamp(issued) not in rows.index for rows in feature_rows.values()
        ):
            # A fresh day alone does not establish the seven-day lag/weather inputs.
            mode, issued = "replay", latest
            daily = raw_daily(hourly)
            feature_rows = issue_feature_rows(city, daily, mode)
            fallback_reason = (
                "Incomplete issue-safe live lag or weather inputs; replay latest archive"
            )
        for horizon in (1, 2, 3):
            version = (
                ForecastModelVersion.objects.filter(
                    city=city,
                    horizon=horizon,
                    available_from__lte=issued,
                    training_end__lte=issued,
                    analysis_run__status="success",
                )
                .order_by("-analysis_run_id", "-available_from", "-pk")
                .first()
            )
            if version is None:
                raise ValueError(
                    f"No issue-safe trained version for {city.slug} h{horizon} at {issued}"
                )
            rows = feature_rows[horizon]
            if pd.Timestamp(issued) not in rows.index:
                raise ValueError(f"No complete issue-time features for {city.slug} on {issued}")
            test = rows.loc[[pd.Timestamp(issued)]].copy()
            if mode == "live":
                test["weather_kind"] = "live_forecast"
            bundle = joblib.load(settings.BASE_DIR / version.artifact_path)
            history = observed_history(daily, rows, horizon)
            point, calibration_info = operational_intervals(bundle, test, history)
            for key, values in point.items():
                test[key] = values
            drivers = top_drivers(bundle["model"], test, bundle["background"], history)
            save_forecasts(city, horizon, version, test, drivers, mode)
            results.append(
                {
                    "city": city.slug,
                    "issued_for_date": str(issued),
                    "target_date": str(test.target_date.iloc[0].date()),
                    "horizon": horizon,
                    "mode": mode,
                    "algorithm": version.algorithm,
                    "point": float(test.prediction.iloc[0]),
                    "model_version": version.pk,
                    "calibration": calibration_info,
                    "data": provenance,
                    "fallback_reason": fallback_reason,
                }
            )
    return results


def fetch_live_weather():
    day = timezone.localdate()
    return ForecastWeatherSource().execute(
        "load", start=str(day), end=str(day + timedelta(days=4)), mode="live"
    )


def refresh_live_pm():
    end = timezone.now()
    return OpenAQSource().execute(
        "load", start=(end - timedelta(days=10)).isoformat(), end=end.isoformat()
    )
