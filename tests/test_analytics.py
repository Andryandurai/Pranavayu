"""Phase 3A synthetic fixtures are deliberately confined to these tests."""

import json
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
import responses
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient
from sklearn.ensemble import RandomForestRegressor

from apps.analytics.aggregation import aggregate_daily, aggregate_monthly, build_tables
from apps.analytics.audit import exclude_unverified, reflag
from apps.analytics.descriptive import diwali_offset, exceedances
from apps.analytics.deweather import WEATHER, fit_city, normalise
from apps.analytics.models import AnalysisRun, CityHourly, CitySeries, StationEligibility
from apps.ingest.quality import flag_readings, quarter_variation
from apps.ingest.units import IST
from apps.warehouse.models import City, Pollutant, Reading
from tests.factories import IngestionRunFactory, StationFactory


@pytest.fixture(autouse=True)
def no_external_http():
    with responses.RequestsMock(assert_all_requests_are_fired=False):
        yield


def synthetic_hours(count=24):
    first = datetime(2024, 1, 1, tzinfo=IST)
    return pd.DataFrame(
        {
            "observed_at": [first + timedelta(hours=i) for i in range(count)],
            "value": np.arange(count, dtype=float) + 20,
        }
    )


@pytest.mark.parametrize("hours,valid", [(17, False), (18, True), (24, True)])
def test_daily_completeness(hours, valid):
    daily = aggregate_daily(synthetic_hours(hours), date(2024, 1, 1), date(2024, 1, 1))
    assert bool(pd.notna(daily.value.iloc[0])) == valid
    assert daily.valid_count.iloc[0] == hours


def test_daily_duplicate_quarters_cannot_become_eighteen_hours():
    frame = synthetic_hours(17)
    duplicate = frame.iloc[[0]].copy()
    duplicate.observed_at += timedelta(minutes=15)
    daily = aggregate_daily(pd.concat([frame, duplicate]), date(2024, 1, 1), date(2024, 1, 1))
    assert daily.valid_count.iloc[0] == 17 and pd.isna(daily.value.iloc[0])


@pytest.mark.parametrize("days,valid", [(22, False), (23, True), (30, True)])
def test_monthly_completeness(days, valid):
    daily = pd.DataFrame(
        {
            "date": pd.date_range("2024-04-01", periods=30).date,
            "value": [20.0] * days + [None] * (30 - days),
        }
    )
    monthly = aggregate_monthly(daily, date(2024, 4, 1), date(2024, 4, 30))
    assert bool(pd.notna(monthly.value.iloc[0])) == valid
    assert monthly.valid_count.iloc[0] == days


@pytest.mark.parametrize(
    "offset,in_window", [(-4, False), (-3, True), (0, True), (3, True), (4, False)]
)
def test_official_diwali_windows(offset, in_window):
    result = diwali_offset(date(2024, 10, 31) + timedelta(days=offset))
    assert result == (offset if in_window else None)


def test_diwali_gap_year_is_not_invented():
    assert diwali_offset(date(2021, 11, 4)) is None


def test_exceedances_are_strict_and_skip_missing():
    assert exceedances([None, 15, 15.1, 60, 60.1]) == {
        "valid_days": 4,
        "naaqs_days": 1,
        "who_days": 3,
    }


def quality_rows(value, count=6, varies=False, code="pm25"):
    return [
        {
            "station_id": 1,
            "code": code,
            "observed_at": datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=i),
            "value": value,
            "raw_value": value,
            "quarter_varies": varies,
        }
        for i in range(count)
    ]


def test_positive_frozen_response_flags_but_zero_reporting_floor_does_not():
    assert {r["quality_flag"] for r in flag_readings(quality_rows(20))} == {"stuck"}
    assert {r["quality_flag"] for r in flag_readings(quality_rows(0, code="co"))} == {"ok"}
    assert {r["quality_flag"] for r in flag_readings(quality_rows(20, count=5))} == {"ok"}


def test_changing_quarters_with_equal_hour_means_are_not_stuck():
    samples = [
        (datetime(2024, 1, 1, tzinfo=UTC) + timedelta(minutes=i * 15), [10, 30, 10, 30][i % 4])
        for i in range(24)
    ]
    assert all(quarter_variation(samples).values())
    assert {r["quality_flag"] for r in flag_readings(quality_rows(20, varies=True))} == {"ok"}
    frozen = [(t, 20) for t, v in samples]
    assert not any(quarter_variation(frozen).values())


def test_corrected_flags_keep_other_rules():
    for value, code, expected in [
        (-1, "pm25", "negative"),
        (None, "pm25", "missing"),
        (1001, "pm25", "outlier"),
        (1000, "pm25", "ok"),
    ]:
        row = quality_rows(value, count=1, code=code)[0]
        assert flag_readings([row])[0]["quality_flag"] == expected
        assert row["raw_value"] == value
    positive = quality_rows(20, count=1) + quality_rows(10, count=1, code="pm10")
    assert flag_readings(positive)[0]["quality_flag"] == "pm25_gt_pm10"
    ordinary = quality_rows(10, count=1) + quality_rows(20, count=1, code="pm10")
    assert flag_readings(ordinary)[0]["quality_flag"] == "ok"


def model_fixture():
    frame = synthetic_hours(24 * 40)
    x = np.arange(len(frame), dtype=float)
    for i, feature in enumerate(WEATHER):
        frame[feature] = 5 + i + np.sin(x / (5 + i))
    frame["value"] = 30 + 10 * frame.wind_speed_ms + 3 * np.cos(x / 24)
    return frame


def test_deweather_smoke_is_reproducible_and_has_blocked_holdout():
    frame = model_fixture()
    a = fit_city(frame, n_trees=5, n_samples=300, seed=42)
    b = fit_city(frame, n_trees=5, n_samples=300, seed=42)
    np.testing.assert_array_equal(a[2], b[2])
    assert a[4]["r2"] == b[4]["r2"]
    assert pd.Timestamp(a[4]["train_end"]) < pd.Timestamp(a[4]["holdout_start"]) - timedelta(days=7)
    assert a[4]["normalisation"]["draws"] == 300
    json.dumps(a[4])  # Stored model metadata must serialize even NumPy readiness comparisons.


def test_exact_trend_partition_normalisation_matches_direct_predictions():
    rng = np.random.default_rng(4)
    x = pd.DataFrame(
        rng.normal(size=(50, 3)).astype(np.float32), columns=["date", "wind", "season"]
    )
    model = RandomForestRegressor(n_estimators=5, max_depth=4, random_state=9).fit(
        x.to_numpy(), x.date + x.wind**2
    )
    predictions, inverse, _ = normalise(model, x, 300, seed=42)
    donors = x.to_numpy()[np.random.default_rng(42).integers(0, len(x), size=300)].copy()
    for i in [0, 7, 19, 49]:
        scenario = donors.copy()
        scenario[:, 0] = x.iloc[i, 0]
        np.testing.assert_allclose(predictions[inverse[i]], model.predict(scenario), rtol=1e-12)


@pytest.mark.django_db
def test_unverified_stations_are_marked_and_verified_curator_evidence_is_preserved():
    unverified = StationFactory(external_id="site_293")
    verified = StationFactory(external_id="site_292")
    StationEligibility.objects.create(
        station=verified, evidence={"verified_official_listing": True}
    )
    exclude_unverified()
    assert unverified.analysis_eligibility.excluded_from_city
    assert unverified.analysis_eligibility.excluded_from_spatial
    verified.analysis_eligibility.refresh_from_db()
    assert not verified.analysis_eligibility.excluded_from_city


def create_run():
    return AnalysisRun.objects.create(
        name="phase3a",
        data_start=date(2024, 1, 1),
        data_end=date(2024, 1, 1),
        started_at=timezone.now(),
    )


@pytest.mark.django_db
def test_city_station_means_exclude_unverified_and_do_not_weight_duplicate_reports(tmp_path):
    call_command("seed_reference", verbosity=0)
    city = City.objects.get(slug="delhi")
    pollutant = Pollutant.objects.get(code="pm25")
    stations = [StationFactory(city=city) for _ in range(3)]
    StationEligibility.objects.create(
        station=stations[2], excluded_from_city=True, excluded_from_spatial=True
    )
    ingestion = IngestionRunFactory()
    first = datetime(2024, 1, 1, tzinfo=IST)
    for hour in range(18):
        for station, value in zip(stations, [10, 30, 900], strict=True):
            Reading.objects.create(
                station=station,
                pollutant=pollutant,
                observed_at=first + timedelta(hours=hour),
                value=value,
                raw_value=value,
                ingestion_run=ingestion,
            )
    Reading.objects.create(
        station=stations[0],
        pollutant=pollutant,
        observed_at=first + timedelta(minutes=15),
        value=10,
        raw_value=10,
        ingestion_run=ingestion,
    )
    run = create_run()
    build_tables(run, tmp_path)
    rows = CityHourly.objects.filter(run=run, city=city, pollutant=pollutant)
    assert rows.count() == 18
    assert set(rows.values_list("value", "station_count")) == {(20.0, 2)}
    assert (
        CitySeries.objects.get(run=run, city=city, pollutant=pollutant, frequency="daily").value
        == 20
    )


@pytest.mark.django_db
def test_reflag_command_logic_is_idempotent_and_raw_values_unchanged(tmp_path, settings):
    settings.RAW_DATA_ROOT = tmp_path / "raw"
    station = StationFactory()
    ingestion = IngestionRunFactory()
    call_command("seed_reference", verbosity=0)
    pollutant = Pollutant.objects.get(code="co")
    for hour in range(6):
        Reading.objects.create(
            station=station,
            pollutant=pollutant,
            observed_at=datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=hour),
            value=0,
            raw_value=0,
            quality_flag="stuck",
            ingestion_run=ingestion,
        )
    first = reflag(create_run(), tmp_path / "first")
    second = reflag(create_run(), tmp_path / "second")
    assert first["changed_rows"] == 6 and second["changed_rows"] == 0
    assert set(Reading.objects.values_list("value", "raw_value", "quality_flag")) == {
        (0.0, 0.0, "ok")
    }


@pytest.mark.django_db
def test_analytics_apis_are_read_only_and_do_not_predict_gap():
    call_command("seed_reference", verbosity=0)
    run = create_run()
    run.status = "success"
    run.save()
    city = City.objects.get(slug="delhi")
    pollutant = Pollutant.objects.get(code="pm25")
    CitySeries.objects.create(
        run=run,
        city=city,
        pollutant=pollutant,
        kind="deweathered",
        frequency="daily",
        date=date(2024, 1, 1),
        value=25,
        valid_count=24,
        expected_count=24,
    )
    client = APIClient()
    assert client.get("/api/analytics/coverage/").status_code == 200
    assert client.get("/api/analytics/city/delhi/summary/").status_code == 200
    result = client.get(
        "/api/analytics/city/delhi/series/",
        {"kind": "deweathered", "start": "2021-01-01", "end": "2022-01-01"},
    )
    assert result.status_code == 200 and result.data["count"] == 0
    assert client.post("/api/analytics/city/delhi/series/", {}).status_code == 405
    assert client.get("/api/analytics/city/delhi/series/", {"kind": "forecast"}).status_code == 400
