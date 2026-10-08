import calendar
from datetime import UTC, date, datetime, timedelta

from django.db import connection

from apps.ingest.units import IST, to_utc
from apps.warehouse.models import City


def bounds(start=None, end=None):
    first = date.fromisoformat(start or "2015-01-01")
    last = date.fromisoformat(end) if end else datetime.now(IST).date() - timedelta(days=1)
    if last < first:
        raise ValueError("Completeness end precedes start")
    return first, last, to_utc(first.isoformat()), to_utc((last + timedelta(days=1)).isoformat())


def completeness(start=None, end=None, station=None):
    first, last, lower, upper = bounds(start, end)
    station_sql = "AND r.station_id = %s" if station else ""
    params = [lower, upper] + ([station] if station else [])
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT r.station_id, s.name, c.slug, p.code,
                   date_trunc('month', r.observed_at AT TIME ZONE 'Asia/Kolkata')::date,
                   count(DISTINCT date_trunc('hour', r.observed_at AT TIME ZONE 'Asia/Kolkata'))
                       FILTER (WHERE r.value IS NOT NULL
                               AND r.quality_flag NOT IN ('missing','negative')),
                   count(*) FILTER (WHERE r.quality_flag <> 'ok')
            FROM warehouse_reading r JOIN warehouse_station s ON s.id=r.station_id
              LEFT JOIN warehouse_city c ON c.id=s.city_id
              JOIN warehouse_pollutant p ON p.id=r.pollutant_id
            WHERE r.observed_at >= %s AND r.observed_at < %s {station_sql}
            GROUP BY r.station_id,s.name,c.slug,p.code,5 ORDER BY c.slug,r.station_id,p.code,5
        """,
            params,
        )
        monthly = []
        for station_id, name, city, code, month, present, flagged in cursor.fetchall():
            month_end = date(
                month.year, month.month, calendar.monthrange(month.year, month.month)[1]
            )
            expected = ((min(last, month_end) - max(first, month)).days + 1) * 24
            monthly.append(
                {
                    "station": station_id,
                    "name": name,
                    "city": city,
                    "pollutant": code,
                    "month": month.isoformat(),
                    "hours_present": present,
                    "hours_expected": expected,
                    "percent": round(100 * present / expected, 2),
                    "flagged_rows": flagged,
                }
            )
        # Include completely absent months between each series' first and last
        # records. Expected hours describe the report calendar, not deployment age.
        groups = {}
        for item in monthly:
            groups.setdefault((item["station"], item["pollutant"]), []).append(item)
        for items in groups.values():
            months = {item["month"] for item in items}
            current, stop = (
                date.fromisoformat(items[0]["month"]),
                date.fromisoformat(items[-1]["month"]),
            )
            while current <= stop:
                if str(current) not in months:
                    month_end = date(
                        current.year,
                        current.month,
                        calendar.monthrange(current.year, current.month)[1],
                    )
                    expected = ((min(last, month_end) - max(first, current)).days + 1) * 24
                    monthly.append(
                        {
                            **items[0],
                            "month": str(current),
                            "hours_present": 0,
                            "hours_expected": expected,
                            "percent": 0,
                            "flagged_rows": 0,
                        }
                    )
                current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        monthly.sort(
            key=lambda item: (item["city"] or "", item["station"], item["pollutant"], item["month"])
        )
        cursor.execute(
            f"""
            WITH days AS (
                SELECT r.station_id,p.code,
                       (r.observed_at AT TIME ZONE 'Asia/Kolkata')::date AS day,
                       count(DISTINCT date_trunc('hour',
                           r.observed_at AT TIME ZONE 'Asia/Kolkata'))
                         FILTER (WHERE r.value IS NOT NULL
                                 AND r.quality_flag NOT IN ('missing','negative')) AS hours
                FROM warehouse_reading r JOIN warehouse_pollutant p ON p.id=r.pollutant_id
                WHERE r.observed_at >= %s AND r.observed_at < %s {station_sql}
                GROUP BY r.station_id,p.code,3
            ), intervals AS (
                SELECT station_id,code,min(day) AS first,max(day) AS last
                FROM days GROUP BY station_id,code
            )
            SELECT i.station_id,i.code,g.day::date,coalesce(d.hours,0)
            FROM intervals i CROSS JOIN LATERAL
              generate_series(i.first::timestamp,i.last::timestamp,interval '1 day') g(day)
            LEFT JOIN days d ON d.station_id=i.station_id AND d.code=i.code AND d.day=g.day::date
            WHERE coalesce(d.hours,0) < 18 ORDER BY i.station_id,i.code,g.day
        """,
            params,
        )
        low_days = [
            {"station": s, "pollutant": p, "date": d.isoformat(), "hours": n}
            for s, p, d, n in cursor.fetchall()
        ]
        cursor.execute(
            f"""
            SELECT c.slug,extract(year FROM r.observed_at AT TIME ZONE 'Asia/Kolkata')::int,
                   count(DISTINCT date_trunc('hour',r.observed_at AT TIME ZONE 'Asia/Kolkata')),
                   count(DISTINCT s.id)
            FROM warehouse_reading r JOIN warehouse_station s ON s.id=r.station_id
              JOIN warehouse_city c ON c.id=s.city_id
              JOIN warehouse_pollutant p ON p.id=r.pollutant_id
            WHERE r.observed_at >= %s AND r.observed_at < %s AND p.code='pm25'
              AND r.value IS NOT NULL AND r.quality_flag NOT IN ('missing','negative') {station_sql}
            GROUP BY c.slug,2 ORDER BY c.slug,2
        """,
            params,
        )
        counts = {(c, y): (n, stations) for c, y, n, stations in cursor.fetchall()}
    city_years = []
    for city in City.objects.all():
        for year in range(first.year, last.year + 1):
            expected = (
                (min(last, date(year, 12, 31)) - max(first, date(year, 1, 1))).days + 1
            ) * 24
            present, stations = counts.get((city.slug, year), (0, 0))
            city_years.append(
                {
                    "city": city.slug,
                    "year": year,
                    "pm25_hours": present,
                    "expected_hours": expected,
                    "percent": round(100 * present / expected, 2),
                    "at_least_75_percent": present / expected >= 0.75,
                    "stations": stations,
                }
            )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "start": str(first),
        "end": str(last),
        "definition": (
            "IST calendar hours with a non-null nonnegative concentration; flagged finite values "
            "count as present, not validated. City coverage is union of stations. "
            "Missing days between first and last reported station/pollutant observations "
            "count zero."
        ),
        "station_months": monthly,
        "station_days_under_75_percent": low_days,
        "city_years": city_years,
    }
