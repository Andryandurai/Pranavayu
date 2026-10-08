"""Reconstruct native IST bins and audit real geography/station networks."""

import csv
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.db import connection

from apps.ingest.http import RawCache
from apps.ingest.quality import aggregate_quarters, flag_readings, quarter_variation
from apps.ingest.units import IST, concentration, number
from apps.warehouse.models import City, Reading, Station, WeatherObservation

from .aggregation import aggregate_daily, aggregate_monthly, store_series
from .models import CityCoverage, CityHourly, StationEligibility


def cached_quarters(city, clock_shift_hours=0):
    lookup = dict(
        Station.objects.filter(source__slug="opencity", city=city).values_list("external_id", "pk")
    )
    samples = defaultdict(dict)
    files = []
    cache = RawCache()
    for path in sorted(cache.root.glob(f"opencity/{city.slug}/*.csv")):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "Timestamp" not in reader.fieldnames:
                continue
            columns = {
                code: next(
                    (h for h in reader.fieldnames if h.lower().split(" (")[0] == label), None
                )
                for code, label in [("pm25", "pm2.5"), ("pm10", "pm10")]
            }
            if not columns["pm25"]:
                continue
            _, manifest = cache.local(path)
            files.append(
                dict(path=manifest["path"], sha256=manifest["sha256"], bytes=manifest["bytes"])
            )
            for raw in reader:
                station = lookup.get(raw.get("Station ID"))
                if station is None or not raw.get("Timestamp"):
                    continue
                timestamp = datetime.fromisoformat(raw["Timestamp"])
                if timestamp.tzinfo is None:
                    raise ValueError("OpenCity timestamp lacks the advertised UTC offset")
                timestamp = timestamp.astimezone(UTC) + pd.Timedelta(hours=clock_shift_hours)
                for code, column in columns.items():
                    if column:
                        unit = column.split("(", 1)[1].rstrip(")") if "(" in column else "ug/m3"
                        samples[(station, code)].setdefault(
                            timestamp, concentration(number(raw[column]), unit, code)
                        )
    records = []
    for (station, code), slots in samples.items():
        observations = list(slots.items())
        variation = quarter_variation(observations, IST)
        for observed, value, raw_mean, flag in aggregate_quarters(observations, IST):
            records.append(
                dict(
                    station_id=station,
                    code=code,
                    observed_at=observed,
                    value=value,
                    raw_value=raw_mean,
                    quality_flag=flag,
                    quarter_varies=variation.get(observed.astimezone(IST), False),
                )
            )
    flag_readings(records)
    return pd.DataFrame([r for r in records if r["code"] == "pm25"]), files


def station_hours(city, clock_shift_hours=0):
    records = list(
        Reading.objects.filter(station__city=city, pollutant__code="pm25")
        .exclude(station__source__slug="opencity")
        .values("station_id", "observed_at", "value", "quality_flag")
    )
    historical = pd.DataFrame(records)
    quarters, files = cached_quarters(city, clock_shift_hours)
    frames = [f for f in [historical, quarters] if not f.empty]
    result = pd.concat(frames, ignore_index=True)
    result["observed_at"] = pd.to_datetime(result.observed_at, utc=True)
    excluded = set(
        StationEligibility.objects.filter(excluded_from_city=True).values_list(
            "station_id", flat=True
        )
    )
    result = result[
        (result.quality_flag == "ok") & result.value.notna() & ~result.station_id.isin(excluded)
    ].copy()
    info = pd.DataFrame(
        list(Station.objects.filter(city=city).values("id", "external_id", "name", "source__slug"))
    )
    result = result.merge(info.rename(columns={"id": "station_id"}), on="station_id", how="left")
    result["year"] = result.observed_at.dt.tz_convert(IST).dt.year
    return result, files


def city_hours(stations):
    rows = stations.copy()
    local = rows.observed_at.dt.tz_convert(IST)
    rows["observed_at"] = local.dt.floor("h").dt.tz_convert("UTC")
    station = rows.groupby(["station_id", "observed_at"], as_index=False).value.mean()
    return station.groupby("observed_at", as_index=False).agg(
        value=("value", "mean"), station_count=("station_id", "nunique")
    )


def weather_frame(city):
    fields = [
        "observed_at",
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
    frame = pd.DataFrame(
        list(WeatherObservation.objects.filter(city=city, source__slug="openmeteo").values(*fields))
    )
    frame["observed_at"] = pd.to_datetime(frame.observed_at, utc=True)
    # ERA5 values are provided at UTC clock hours, the midpoint of canonical IST bins.
    frame["observed_at"] = frame.observed_at - pd.Timedelta(minutes=30)
    return frame


def join_weather(hourly, weather):
    return hourly.merge(weather, on="observed_at", how="left", validate="one_to_one")


def fixed_panel(stations):
    old = set(stations.loc[stations.year.between(2015, 2019), "external_id"])
    recent = set(stations.loc[stations.year.between(2024, 2025), "external_id"])
    common = sorted(old & recent)
    # Match physical CPCB site IDs across provider-specific database identities.
    return stations[stations.external_id.isin(common)], common


def geography_audit(output):
    grids = []
    for city in City.objects.all():
        paths = sorted((Path(settings.RAW_DATA_ROOT) / "openmeteo" / city.slug).glob("*.json"))
        points = set()
        for path in paths:
            if path.name.endswith(".manifest.json"):
                continue
            payload = json.loads(path.read_text())
            if "latitude" in payload and "longitude" in payload:
                points.add((payload["longitude"], payload["latitude"]))
        grids.append(
            dict(
                city=city.slug,
                requested_lon=city.location.x,
                requested_lat=city.location.y,
                returned_grid_points=sorted(points),
            )
        )
    records = []
    with connection.cursor() as cursor:
        for grid in grids:
            point = (
                grid["returned_grid_points"][0]
                if grid["returned_grid_points"]
                else (grid["requested_lon"], grid["requested_lat"])
            )
            cursor.execute(
                """SELECT s.id,s.external_id,s.name,d.slug,c.slug,dist.name,
                ST_Covers(dist.geometry,s.location),
                ST_Distance(s.location::geography,c.location::geography)/1000,
                ST_Distance(s.location::geography,ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography)/1000,
                (SELECT string_agg(q.name,', ' ORDER BY q.id) FROM warehouse_district q
                  WHERE ST_Covers(q.geometry,s.location)),
                coalesce(e.excluded_from_city,false)
                FROM warehouse_station s JOIN warehouse_city c ON c.id=s.city_id
                JOIN ingest_datasource d ON d.id=s.source_id
                LEFT JOIN ingest_citydistrictlink link ON link.city_id=c.id
                LEFT JOIN warehouse_district dist ON dist.id=link.district_id
                LEFT JOIN analytics_stationeligibility e ON e.station_id=s.id
                WHERE c.slug=%s ORDER BY s.id""",
                [point[0], point[1], grid["city"]],
            )
            keys = [
                "station_id",
                "site_id",
                "station",
                "source",
                "city",
                "city_district",
                "inside_city_district",
                "requested_point_distance_km",
                "grid_point_distance_km",
                "actual_districts",
                "excluded",
            ]
            records.extend(dict(zip(keys, row, strict=True)) for row in cursor.fetchall())
    pd.DataFrame(records).to_csv(output / "station_geography.csv", index=False)
    (output / "weather_grids.json").write_text(json.dumps(grids, indent=2))
    return records, grids


def snapshot_city(run, output, city, stations, weather):
    hourly = join_weather(city_hours(stations), weather)
    from apps.warehouse.models import Pollutant

    pm = Pollutant.objects.get(code="pm25")
    fields = list(weather.columns.drop("observed_at"))
    objects = [
        CityHourly(
            run=run,
            city=city,
            pollutant=pm,
            observed_at=r.observed_at,
            value=r.value,
            station_count=r.station_count,
            weather={
                key: float(getattr(r, key)) if pd.notna(getattr(r, key)) else None for key in fields
            },
        )
        for r in hourly.itertuples()
    ]
    CityHourly.objects.bulk_create(objects, batch_size=2000)
    daily = aggregate_daily(hourly, run.data_start, run.data_end)
    monthly = aggregate_monthly(daily, run.data_start, run.data_end)
    store_series(run, city, pm, daily, "raw", "daily")
    store_series(run, city, pm, monthly, "raw", "monthly")
    coverage = []
    for year, days in daily.groupby(pd.to_datetime(daily.date).dt.year):
        hours, valid = int(days.valid_count.sum()), int(days.value.notna().sum())
        item = dict(
            year=int(year),
            hours_present=hours,
            hours_expected=len(days) * 24,
            valid_days=valid,
            expected_days=len(days),
            valid_months=int(
                monthly.loc[pd.to_datetime(monthly.date).dt.year == year, "value"].notna().sum()
            ),
            eligible=hours / (len(days) * 24) >= 0.75 and valid / len(days) >= 0.75,
        )
        CityCoverage.objects.create(run=run, city=city, pollutant=pm, **item)
        coverage.append({"city": city.slug, **item})
    hourly.to_pickle(output / f"{city.slug}_hourly.pkl")
    daily.to_csv(output / f"{city.slug}_raw_daily.csv", index=False)
    weather.to_pickle(output / f"{city.slug}_weather.pkl")
    return hourly, daily, coverage


def hyderabad_audit(stations, daily):
    rows = stations[stations.year == 2025]
    days = daily[pd.to_datetime(daily.date).dt.year == 2025].dropna(subset=["value"])
    stats = []
    for (site, name), group in rows.groupby(["external_id", "name"]):
        values = group.value
        stats.append(
            dict(
                site=site,
                name=name,
                hours=len(group),
                hourly_max=float(values.max()),
                hourly_mean=float(values.mean()),
                distinct_values=values.nunique(),
                maximum_repeat_count=int((values == values.max()).sum()),
                value_exactly_60=int((values == 60).sum()),
            )
        )
    return dict(
        valid_days=len(days),
        daily_max=float(days.value.max()),
        annual_mean=float(days.value.mean()),
        above_60=int((days.value > 60).sum()),
        above_15=int((days.value > 15).sum()),
        stations=stats,
    )
