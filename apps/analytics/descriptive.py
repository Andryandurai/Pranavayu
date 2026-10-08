from datetime import date, timedelta

import numpy as np
import pandas as pd

from apps.warehouse.models import City

from .aggregation import analysis_dataframe
from .models import CityCoverage, CityMetric, CitySeries

# Government calendars, rather than calculated astronomical festival dates.
DIWALI = {
    2015: date(2015, 11, 11),  # https://surveyofindia.gov.in/files/RONo.10.pdf
    2016: date(
        2016, 10, 30
    ),  # https://nationalarchives.nic.in/sites/default/files/2023-07/holiday-list-2016-english_0_0.pdf
    2017: date(
        2017, 10, 19
    ),  # https://kandlacustoms.gov.in/wp-content/uploads/2017/04/Holidays-2017.pdf
    2018: date(2018, 11, 7),  # https://surveyofindia.gov.in/files/Holiday%20List%202018.pdf
    2019: date(2019, 10, 27),  # https://surveyofindia.gov.in/files/Holidays%202019.pdf
    2024: date(
        2024, 10, 31
    ),  # https://www.surveyofindia.gov.in/documents/circulars/document-82049-spg-ro8-19-12-2023.pdf
    2025: date(2025, 10, 20),  # https://necouncil.gov.in/sites/default/files/nec%20cal%202025.pdf
}
CALENDAR_SOURCES = {
    2015: "https://surveyofindia.gov.in/files/RONo.10.pdf",
    2016: "https://nationalarchives.nic.in/sites/default/files/2023-07/holiday-list-2016-english_0_0.pdf",
    2017: "https://kandlacustoms.gov.in/wp-content/uploads/2017/04/Holidays-2017.pdf",
    2018: "https://surveyofindia.gov.in/files/Holiday%20List%202018.pdf",
    2019: "https://surveyofindia.gov.in/files/Holidays%202019.pdf",
    2024: "https://www.surveyofindia.gov.in/documents/circulars/document-82049-spg-ro8-19-12-2023.pdf",
    2025: "https://necouncil.gov.in/sites/default/files/nec%20cal%202025.pdf",
}


def diwali_offset(day):
    event = DIWALI.get(day.year)
    delta = (day - event).days if event else None
    return delta if delta is not None and -3 <= delta <= 3 else None


def exceedances(values):
    valid = np.asarray(values, dtype=float)
    valid = valid[np.isfinite(valid)]
    return {
        "valid_days": len(valid),
        "naaqs_days": int((valid > 60).sum()),
        "who_days": int((valid > 15).sum()),
    }


def season(month):
    if month in [12, 1, 2]:
        return "winter"
    if month in [3, 4, 5]:
        return "pre_monsoon"
    if month in [6, 7, 8, 9]:
        return "monsoon"
    return "post_monsoon"


def winter_smog(day):
    return day.month == 1 or day.month >= 11 or (day.month == 10 and day.day >= 15)


def era_difference(daily, seed=42, samples=500):
    """Year-and-seven-calendar-day block bootstrap of observed daily means."""
    rows = daily.dropna(subset=["value"])
    groups = {
        int(y): group.sort_values("date")
        for y, group in rows.groupby(pd.to_datetime(rows.date).dt.year)
    }
    old = [y for y in groups if 2015 <= y <= 2019]
    recent = [y for y in groups if 2024 <= y <= 2025]
    if not old or not recent:
        return {"status": "unavailable", "reason": "At least one observed era lacks eligible years"}
    rng = np.random.default_rng(seed)

    def period(years, resample=False):
        means = []
        chosen = rng.choice(years, size=len(years), replace=True) if resample else years
        for year in chosen:
            group = groups[year]
            if resample:
                # Actual consecutive seven-day calendar blocks; gaps end a block.
                blocks = []
                block = []
                previous = None
                for row in group.itertuples():
                    if block and (len(block) == 7 or row.date - previous != timedelta(days=1)):
                        blocks.append(np.array(block))
                        block = []
                    block.append(row.value)
                    previous = row.date
                if block:
                    blocks.append(np.array(block))
                sampled = []
                count = 0
                while count < len(group):
                    block = blocks[rng.integers(len(blocks))]
                    sampled.append(block)
                    count += len(block)
                means.append(np.concatenate(sampled)[: len(group)].mean())
            else:
                means.append(group.value.mean())
        return float(np.mean(means))

    baseline, current = period(old), period(recent)
    draws = np.array([period(recent, True) - period(old, True) for _ in range(samples)])
    return {
        "status": "descriptive",
        "baseline_years": old,
        "recent_years": recent,
        "baseline_mean": baseline,
        "recent_mean": current,
        "difference": current - baseline,
        "ci95_low": float(np.quantile(draws, 0.025)),
        "ci95_high": float(np.quantile(draws, 0.975)),
        "samples": samples,
        "block_days": 7,
        "seed": seed,
        "interpretation": (
            "Descriptive difference with resampling uncertainty; not a policy effect; "
            "station mix and source changed."
        ),
    }


def describe(run, output, seed=42):
    results = {
        "annual": [],
        "climatology": [],
        "diurnal": [],
        "weekday": [],
        "diwali": [],
        "winter_smog": [],
        "change": [],
    }
    for city in City.objects.all():
        years = set(
            CityCoverage.objects.filter(
                run=run, city=city, pollutant__code="pm25", eligible=True
            ).values_list("year", flat=True)
        )
        daily = pd.DataFrame(
            list(
                CitySeries.objects.filter(
                    run=run, city=city, pollutant__code="pm25", kind="raw", frequency="daily"
                ).values("date", "value")
            )
        )
        daily = daily[pd.to_datetime(daily.date).dt.year.isin(years)].dropna(subset=["value"])
        monthly = pd.DataFrame(
            list(
                CitySeries.objects.filter(
                    run=run, city=city, pollutant__code="pm25", kind="raw", frequency="monthly"
                ).values("date", "value")
            )
        )
        monthly = monthly[pd.to_datetime(monthly.date).dt.year.isin(years)].dropna(subset=["value"])
        for year, group in daily.groupby(pd.to_datetime(daily.date).dt.year):
            value = {
                "city": city.slug,
                "year": int(year),
                "annual_mean_pm25": float(group.value.mean()),
                **exceedances(group.value),
            }
            results["annual"].append(value)
            CityMetric.objects.create(
                run=run, city=city, name="annual_pm25", year=int(year), result=value
            )
            weekdays = pd.to_datetime(group.date).dt.weekday
            weekday, weekend = group.loc[weekdays < 5, "value"], group.loc[weekdays >= 5, "value"]
            value = {
                "city": city.slug,
                "year": int(year),
                "weekday_mean": float(weekday.mean()),
                "weekend_mean": float(weekend.mean()),
                "weekday_valid_days": len(weekday),
                "weekend_valid_days": len(weekend),
                "weekend_minus_weekday": float(weekend.mean() - weekday.mean()),
            }
            results["weekday"].append(value)
            CityMetric.objects.create(
                run=run, city=city, name="weekday_weekend", year=int(year), result=value
            )
            winter = group.date.map(winter_smog)
            value = {
                "city": city.slug,
                "year": int(year),
                "winter_mean": float(group.loc[winter, "value"].mean()) if winter.any() else None,
                "rest_mean": float(group.loc[~winter, "value"].mean()) if (~winter).any() else None,
                "winter_valid_days": int(winter.sum()),
                "rest_valid_days": int((~winter).sum()),
                "window": "Jan 1–31 plus Oct 15–Dec 31 within this eligible calendar year",
            }
            results["winter_smog"].append(value)
            CityMetric.objects.create(
                run=run, city=city, name="winter_smog", year=int(year), result=value
            )
        for row in daily.itertuples():
            offset = diwali_offset(row.date)
            if offset is not None:
                results["diwali"].append(
                    {
                        "city": city.slug,
                        "year": row.date.year,
                        "date": str(row.date),
                        "offset": offset,
                        "value": row.value,
                    }
                )
        if not monthly.empty:
            for month, group in monthly.groupby(pd.to_datetime(monthly.date).dt.month):
                results["climatology"].append(
                    {
                        "city": city.slug,
                        "month": int(month),
                        "mean_pm25": float(group.value.mean()),
                        "year_months": len(group),
                    }
                )
        hourly = analysis_dataframe(city.slug, run)
        if not hourly.empty:
            local = hourly.observed_at.dt.tz_convert("Asia/Kolkata")
            hourly = hourly.loc[local.dt.year.isin(years)].copy()
            local = hourly.observed_at.dt.tz_convert("Asia/Kolkata")
            hourly["season"] = local.dt.month.map(season)
            hourly["hour"] = local.dt.hour
            for (label, hour), group in hourly.groupby(["season", "hour"]):
                results["diurnal"].append(
                    {
                        "city": city.slug,
                        "season": label,
                        "hour": int(hour),
                        "mean_pm25": float(group.value.mean()),
                        "valid_hours": len(group),
                    }
                )
        change = {"city": city.slug, **era_difference(daily, seed)}
        results["change"].append(change)
        CityMetric.objects.create(run=run, city=city, name="era_difference", result=change)
        for name in ["climatology", "diurnal", "diwali"]:
            CityMetric.objects.create(
                run=run,
                city=city,
                name=name,
                result={"rows": [r for r in results[name] if r["city"] == city.slug]},
            )
    results["annual"].sort(key=lambda r: (r["year"], -r["annual_mean_pm25"]))
    for year in {r["year"] for r in results["annual"]}:
        for rank, row in enumerate([r for r in results["annual"] if r["year"] == year], 1):
            row["rank"] = rank
            CityMetric.objects.filter(
                run=run, city__slug=row["city"], name="annual_pm25", year=year
            ).update(result=row)
    for name, rows in results.items():
        pd.DataFrame(rows).to_csv(output / f"descriptive_{name}.csv", index=False)
    return results
