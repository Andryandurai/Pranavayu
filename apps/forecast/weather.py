"""Phase 2 cache/lifecycle and explicit lead-time provenance for forecast weather."""

import json
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from django.conf import settings
from django.utils import timezone

from apps.ingest.base import Source, insert_batch
from apps.warehouse.models import City

from .models import ForecastWeather

WEATHER_VARIABLES = {
    "temperature_2m": "temperature_c",
    "relative_humidity_2m": "relative_humidity",
    "wind_speed_10m": "wind_speed_ms",
    "wind_direction_10m": "wind_dir_deg",
    "precipitation": "precipitation_mm",
    "cloud_cover": "total_cloud_cover",
    "surface_pressure": "surface_pressure_hpa",
    "boundary_layer_height": "boundary_layer_height_m",
}
REQUIRED_WEATHER = tuple(v for v in WEATHER_VARIABLES.values() if v != "boundary_layer_height_m")


def issue_end(day):
    first_next = datetime.combine(
        day + timedelta(days=1), datetime.min.time(), ZoneInfo("Asia/Kolkata")
    )
    return pd.Timestamp((first_next - timedelta(microseconds=1)).astimezone(UTC))


def daily_weather(payload, horizon, mode="archive", fetched_at=None):
    if payload.get("utc_offset_seconds") != 0:
        raise ValueError("Forecast weather must have UTC response timestamps")
    hourly = payload["hourly"]
    times = pd.to_datetime(hourly["time"], utc=True)
    lead = horizon + 1
    frame = pd.DataFrame({"valid_at": times})
    for variable, feature in WEATHER_VARIABLES.items():
        key = f"{variable}_previous_day{lead}" if mode == "archive" else variable
        if variable == "wind_speed_10m" and payload["hourly_units"].get(key) != "m/s":
            raise ValueError("Forecast wind speed must be m/s")
        frame[feature] = hourly.get(key, [None] * len(frame))
    frame["date"] = times.tz_convert("Asia/Kolkata").date
    result = []
    for day, group in frame.groupby("date"):
        issued = day - timedelta(days=horizon)
        if mode == "live" and issued != pd.Timestamp(fetched_at).tz_convert("Asia/Kolkata").date():
            continue
        available = (
            pd.Timestamp(
                max(
                    v.to_pydatetime() - timedelta(days=lead) + timedelta(hours=12)
                    for v in group.valid_at
                )
            )
            if mode == "archive"
            else pd.Timestamp(fetched_at)
        )
        if available > issue_end(issued):
            continue
        features = {}
        counts = {}
        for feature in WEATHER_VARIABLES.values():
            values = pd.to_numeric(group[feature], errors="coerce")
            counts[feature] = int(values.notna().sum())
            if feature == "wind_dir_deg":
                radians = np.deg2rad(values)
                features["wind_sin"] = float(np.sin(radians).mean()) if counts[feature] else None
                features["wind_cos"] = float(np.cos(radians).mean()) if counts[feature] else None
            else:
                value = values.sum(min_count=1) if feature == "precipitation_mm" else values.mean()
                if feature == "total_cloud_cover":
                    value /= 100
                features[feature] = (
                    float(value) if pd.notna(value) and counts[feature] >= 24 else None
                )
        if len(group) != 24 or any(counts[k] < 24 for k in REQUIRED_WEATHER):
            continue
        result.append(
            dict(
                issued_for_date=issued,
                target_date=day,
                horizon=horizon,
                available_by=available.to_pydatetime(),
                lead_days=lead if mode == "archive" else 0,
                features=features,
                hours=len(group),
                provenance={
                    "availability_semantics": "conservative bound: valid_time - lead_days*24h + 12h"
                    if mode == "archive"
                    else "actual retrieval time",
                    "latest_valid_at": group.valid_at.max().isoformat(),
                    "variable_non_null_hours": counts,
                    "model": "gfs_global",
                    "timezone": "UTC",
                    "exact_historical_publication_time": None,
                },
            )
        )
    return result


class ForecastWeatherSource(Source):
    slug = "openmeteo-forecast"
    name = "Open-Meteo GFS archived lead forecasts and live forecasts"
    url = "https://open-meteo.com/en/docs/previous-runs-api"
    licence = "CC BY 4.0; attribute Open-Meteo and NOAA. Public non-commercial API."
    access_method = "api"

    def fetch(self, city, first, last, mode="archive"):
        endpoint = (
            "https://previous-runs-api.open-meteo.com/v1/forecast"
            if mode == "archive"
            else "https://api.open-meteo.com/v1/forecast"
        )
        hourly = (
            ",".join(f"{v}_previous_day{lead}" for lead in (2, 3, 4) for v in WEATHER_VARIABLES)
            if mode == "archive"
            else ",".join(WEATHER_VARIABLES)
        )
        return self.download_asset(
            endpoint,
            f"forecast/{mode}/{city.slug}/{first}_{last}.json",
            params={
                "latitude": city.location.y,
                "longitude": city.location.x,
                "start_date": str(first),
                "end_date": str(last),
                "hourly": hourly,
                "models": "gfs_global",
                "timezone": "UTC",
                "wind_speed_unit": "ms",
            },
            metadata={
                "city": city.slug,
                "model": "gfs_global",
                "mode": mode,
                "lead_days": [2, 3, 4] if mode == "archive" else [],
                "publication_margin_hours": 12,
                "source_docs": self.url,
            },
        )

    def load_payload(self, payload, city, asset, mode="archive", fetched_at=None):
        rows = []
        for horizon in (1, 2, 3):
            for record in daily_weather(payload, horizon, mode, fetched_at):
                rows.append(
                    ForecastWeather(
                        city=city,
                        source=self.source,
                        ingestion_run=self.run,
                        asset=asset,
                        mode=mode,
                        **record,
                    )
                )
        self.run.rows_fetched += len(rows)
        self.run.rows_inserted += len(insert_batch(ForecastWeather, rows))
        self.run.save(update_fields=["rows_fetched", "rows_inserted", "updated_at"])
        return len(rows)

    def load(self, cities=None, start="2024-01-01", end="2026-01-03", mode="archive", **options):
        for city in City.objects.filter(slug__in=cities or settings.FORECAST_CITIES).order_by(
            "slug"
        ):
            first = pd.Timestamp(start).date()
            final = pd.Timestamp(end).date()
            while first <= final:
                last = min(final, first + timedelta(days=89))
                try:
                    request_start = (
                        first - timedelta(days=1) if first > pd.Timestamp(start).date() else first
                    )
                    path, asset = self.fetch(city, request_start, last, mode)
                    fetched = timezone.now()
                    count = self.load_payload(
                        json.loads(path.read_text()), city, asset, mode, fetched
                    )
                    self.event(
                        "forecast_window_loaded",
                        city=city.slug,
                        start=str(first),
                        end=str(last),
                        rows=count,
                        cache_hit=self.cache.last_cache_hit,
                    )
                except Exception as exc:
                    self.fail_asset(f"{city.slug}:{first}:{last}", exc)
                first = last + timedelta(days=1)
