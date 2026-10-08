from datetime import timedelta

import pandas as pd
from django.db import connection, transaction

from apps.ingest.units import IST
from apps.warehouse.models import City, Pollutant

from .models import CityCoverage, CityHourly, CitySeries


def aggregate_daily(frame, start, end):
    """Calendar days in IST; 18 distinct valid hour bins, without filling values."""
    calendar_days = pd.date_range(start, end, freq="D")
    if frame.empty:
        return pd.DataFrame(
            {"date": calendar_days.date, "value": None, "valid_count": 0, "expected_count": 24}
        )
    rows = frame.copy()
    local = pd.to_datetime(rows["observed_at"], utc=True).dt.tz_convert(IST)
    rows["date"] = local.dt.date
    rows["hour"] = local.dt.floor("h")
    rows = rows.dropna(subset=["value"])
    rows = rows.groupby(["date", "hour"], as_index=False).value.mean()
    daily = rows.groupby("date").agg(value=("value", "mean"), valid_count=("hour", "nunique"))
    daily = daily.reindex(calendar_days.date)
    daily["valid_count"] = daily["valid_count"].fillna(0).astype(int)
    daily.loc[daily.valid_count < 18, "value"] = float("nan")
    daily["expected_count"] = 24
    return daily.rename_axis("date").reset_index()


def aggregate_monthly(daily, start, end):
    rows = daily.copy()
    rows["month"] = pd.to_datetime(rows["date"]).dt.to_period("M")
    result = []
    for month, group in rows.groupby("month"):
        first = month.start_time.date()
        expected = (min(end, month.end_time.date()) - max(start, first)).days + 1
        valid = group["value"].notna().sum()
        result.append(
            {
                "date": first,
                "value": float(group.value.mean()) if valid / expected >= 0.75 else None,
                "valid_count": int(valid),
                "expected_count": expected,
            }
        )
    return pd.DataFrame(result, columns=["date", "value", "valid_count", "expected_count"])


def nullable(value):
    return float(value) if pd.notna(value) else None


def store_series(run, city, pollutant, frame, kind, frequency):
    objects = [
        CitySeries(
            run=run,
            city=city,
            pollutant=pollutant,
            kind=kind,
            frequency=frequency,
            date=r.date,
            value=nullable(r.value),
            valid_count=int(r.valid_count),
            expected_count=int(r.expected_count),
            sampling_se=nullable(getattr(r, "sampling_se", None)),
        )
        for r in frame.itertuples()
    ]
    CitySeries.objects.bulk_create(objects, batch_size=2000)


def analysis_dataframe(city, run=None, pollutant="pm25"):
    rows = CityHourly.objects.filter(city__slug=city, pollutant__code=pollutant)
    if run is None:
        from .models import AnalysisRun

        run = (
            AnalysisRun.objects.filter(status="success", name__in=["phase3a", "phase3a2"])
            .order_by("-id")
            .first()
        )
        if run is None:
            return pd.DataFrame()
    rows = rows.filter(run=run).order_by("observed_at")
    frame = pd.DataFrame(list(rows.values("observed_at", "value", "station_count", "weather")))
    if not frame.empty:
        weather = pd.json_normalize(frame.pop("weather"))
        frame = pd.concat([frame, weather], axis=1)
        frame["observed_at"] = pd.to_datetime(frame["observed_at"], utc=True)
    return frame


def build_tables(run, output):
    start, end = run.data_start, run.data_end
    lower = pd.Timestamp(start, tz=IST).to_pydatetime()
    upper = pd.Timestamp(end + timedelta(days=1), tz=IST).to_pydatetime()
    with transaction.atomic(), connection.cursor() as cursor:
        CityHourly.objects.filter(run=run).delete()
        CityCoverage.objects.filter(run=run).delete()
        CitySeries.objects.filter(run=run, kind="raw").delete()
        cursor.execute(
            """INSERT INTO analytics_cityhourly
            (run_id,city_id,pollutant_id,observed_at,value,station_count,weather)
            WITH station_hours AS (
                SELECT s.id AS station_id,s.city_id,r.pollutant_id,
                 date_trunc('hour',r.observed_at AT TIME ZONE 'Asia/Kolkata')
                   AT TIME ZONE 'Asia/Kolkata' AS hour,
                 avg(r.value) AS value
                FROM warehouse_reading r JOIN warehouse_station s ON s.id=r.station_id
                LEFT JOIN analytics_stationeligibility e ON e.station_id=s.id
                WHERE r.observed_at >= %s AND r.observed_at < %s AND r.quality_flag='ok'
                  AND r.value IS NOT NULL AND s.city_id IS NOT NULL
                  AND coalesce(e.excluded_from_city,false)=false
                GROUP BY s.id,s.city_id,r.pollutant_id,4
            ), eligible AS (
                SELECT city_id,pollutant_id,hour,avg(value) AS value,count(*) AS n
                FROM station_hours GROUP BY city_id,pollutant_id,hour
            ) SELECT %s,e.city_id,e.pollutant_id,e.hour,e.value,e.n,
             jsonb_build_object('temperature_c',w.temperature_c,'relative_humidity',w.relative_humidity,
                'wind_speed_ms',w.wind_speed_ms,'wind_dir_deg',w.wind_dir_deg,
                'surface_pressure_hpa',w.surface_pressure_hpa,'precipitation_mm',w.precipitation_mm,
                'total_cloud_cover',w.total_cloud_cover,'solar_radiation_wm2',w.solar_radiation_wm2,
                'boundary_layer_height_m',w.boundary_layer_height_m)
            FROM eligible e LEFT JOIN warehouse_weatherobservation w
             ON w.city_id=e.city_id AND w.observed_at=e.hour+interval '30 minutes'
             AND w.source_id=(SELECT id FROM ingest_datasource WHERE slug='openmeteo')""",
            [lower, upper, run.pk],
        )
    all_coverage = []
    for city in City.objects.all():
        for pollutant in Pollutant.objects.all():
            frame = analysis_dataframe(city.slug, run, pollutant.code)
            daily = aggregate_daily(frame, start, end)
            monthly = aggregate_monthly(daily, start, end)
            store_series(run, city, pollutant, daily, "raw", "daily")
            store_series(run, city, pollutant, monthly, "raw", "monthly")
            for year in range(start.year, end.year + 1):
                first = max(start, start.replace(year=year, month=1, day=1))
                last = min(end, end.replace(year=year, month=12, day=31))
                days = daily[(pd.to_datetime(daily.date).dt.year == year)]
                months = monthly[pd.to_datetime(monthly.date).dt.year == year]
                expected = (last - first).days + 1
                valid = int(days.value.notna().sum())
                hours = int(days.valid_count.sum())
                record = CityCoverage.objects.create(
                    run=run,
                    city=city,
                    pollutant=pollutant,
                    year=year,
                    hours_present=hours,
                    hours_expected=expected * 24,
                    valid_days=valid,
                    expected_days=expected,
                    valid_months=int(months.value.notna().sum()),
                    eligible=valid / expected >= 0.75 and hours / (expected * 24) >= 0.75,
                )
                all_coverage.append(
                    {
                        "city": city.slug,
                        "pollutant": pollutant.code,
                        "year": year,
                        "hours": hours,
                        "expected_hours": expected * 24,
                        "valid_days": valid,
                        "expected_days": expected,
                        "valid_months": record.valid_months,
                        "eligible": record.eligible,
                    }
                )
            if pollutant.code == "pm25":
                daily.to_csv(output / f"{city.slug}_raw_daily.csv", index=False)
                monthly.to_csv(output / f"{city.slug}_raw_monthly.csv", index=False)
    pd.DataFrame(all_coverage).to_csv(output / "analysis_coverage.csv", index=False)
    return {"hourly_rows": CityHourly.objects.filter(run=run).count(), "coverage": all_coverage}
