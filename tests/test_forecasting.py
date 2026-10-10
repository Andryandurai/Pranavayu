from datetime import date

import numpy as np
import pandas as pd
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.analytics.models import AnalysisRun
from apps.forecast.data import (
    FEATURES,
    WEATHER_FEATURES,
    feature_provenance,
    make_features,
    raw_daily,
    rolling_origins,
    training_segments,
)
from apps.forecast.metrics import aqi_category, conformal_radius, dm_test, scores
from apps.forecast.models import Forecast, ForecastModelVersion
from apps.forecast.operations import select_issue_mode
from apps.forecast.weather import daily_weather, issue_end
from tests.factories import CityFactory


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, "good"),
        (30, "good"),
        (30.1, "satisfactory"),
        (60, "satisfactory"),
        (60.1, "moderate"),
        (90, "moderate"),
        (90.1, "poor"),
        (120, "poor"),
        (120.1, "very_poor"),
        (250, "very_poor"),
        (250.1, "severe"),
    ],
)
def test_cpcb_pm25_categories(value, expected):
    assert aqi_category(value) == expected


def test_conformal_empirical_coverage_and_small_sample_guard():
    rng = np.random.default_rng(22)
    calibration = rng.normal(size=1000)
    future = rng.normal(size=20000)
    for alpha in (0.2, 0.05):
        radius = conformal_radius(calibration, alpha)
        assert abs(np.mean(np.abs(future) <= radius) - (1 - alpha)) < 0.025
    with pytest.raises(ValueError, match="too small"):
        conformal_radius([1, 2, 3], 0.05)


def feature_fixture():
    times = pd.date_range("2024-01-01", periods=24 * 32, freq="h", tz="Asia/Kolkata").tz_convert(
        "UTC"
    )
    hourly = pd.DataFrame({"observed_at": times, "value": np.arange(len(times)) % 50 + 20.0})
    daily = raw_daily(hourly, "2024-01-01", "2024-02-01")
    records = [
        {
            "issued_for_date": day.date(),
            "available_by": issue_end(day.date()) - pd.Timedelta(hours=12),
            "asset_id": 1,
            "features": {name: float(i + 1) for i, name in enumerate(WEATHER_FEATURES)},
        }
        for day in daily.index
    ]
    return hourly, daily, records


def test_every_feature_available_by_issue_end_and_future_pm_has_no_effect():
    hourly, daily, records = feature_fixture()
    issued = pd.Timestamp("2024-01-20")
    rows = make_features(daily, records, 3)
    row = rows.loc[issued]
    provenance = feature_provenance(row, 3)
    cutoff = issue_end(issued.date())
    assert all(
        pd.Timestamp(stamp) <= cutoff for stamp in provenance["feature_availability"].values()
    )
    assert provenance["weather_kind"] == "archived_forecast"
    altered = hourly.copy()
    altered.loc[altered.observed_at > cutoff, "value"] = 99999
    after = make_features(raw_daily(altered, "2024-01-01", "2024-02-01"), records, 3)
    np.testing.assert_array_equal(row[FEATURES].to_numpy(), after.loc[issued, FEATURES].to_numpy())
    bad = row.copy()
    bad["weather_available_by"] = cutoff + pd.Timedelta(hours=1)
    with pytest.raises(ValueError, match="Future"):
        feature_provenance(bad, 3)
    bad["weather_kind"] = "perfect_prognosis_observed"
    with pytest.raises(ValueError, match="observed"):
        feature_provenance(bad, 3)


def test_rolling_origins_and_tuning_calibration_labels_are_purged():
    dates = pd.date_range("2024-01-01", "2025-12-28")
    rows = pd.DataFrame(
        {"issued_for_date": dates, "target_date": dates + pd.Timedelta(days=3), "y": 20.0},
        index=dates,
    )
    windows = list(rolling_origins(rows, "2025-12-31"))
    assert len(windows) == 7
    seen = []
    for month, origin, train, test in windows:
        assert (train.target_date <= origin).all()
        assert (test.target_date > origin).all()
        assert train.index.is_monotonic_increasing and test.index.is_monotonic_increasing
        fit, tune, final_fit, calibration = training_segments(train, origin)
        assert fit.target_date.max() < tune.issued_for_date.min()
        assert tune.target_date.max() < calibration.issued_for_date.min()
        assert final_fit.target_date.max() < calibration.issued_for_date.min()
        assert calibration.target_date.max() <= test.issued_for_date.min()
        assert str(test.issued_for_date.iloc[0].to_period("M")) == month
        seen.extend(test.target_date)
    assert len(seen) == 184 and len(set(seen)) == 184
    assert min(seen) == pd.Timestamp("2025-07-01")
    assert max(seen) == pd.Timestamp("2025-12-31")


def test_archived_leads_utc_to_ist_and_missing_blh_remains_null():
    from apps.forecast.weather import WEATHER_VARIABLES

    times = pd.date_range("2025-07-01", periods=48, freq="h", tz="UTC")
    payload = {
        "utc_offset_seconds": 0,
        "hourly": {"time": times.strftime("%Y-%m-%dT%H:%M").tolist()},
        "hourly_units": {},
    }
    for variable in WEATHER_VARIABLES:
        key = f"{variable}_previous_day4"
        payload["hourly"][key] = [None if variable == "boundary_layer_height" else 5.0] * 48
        payload["hourly_units"][key] = "m/s" if variable == "wind_speed_10m" else "unit"
    records = daily_weather(payload, 3)
    assert len(records) == 1
    row = records[0]
    assert row["target_date"] == date(2025, 7, 2)
    assert row["issued_for_date"] == date(2025, 6, 29)
    assert row["hours"] == 24 and row["lead_days"] == 4
    assert row["available_by"] <= issue_end(row["issued_for_date"])
    assert row["features"]["boundary_layer_height_m"] is None
    assert row["features"]["precipitation_mm"] == 120
    assert row["provenance"]["exact_historical_publication_time"] is None


def test_replay_selection_needs_no_openaq_key():
    today = date(2026, 10, 10)
    last = date(2025, 12, 31)
    assert select_issue_mode(False, last, today) == ("replay", last)
    assert select_issue_mode(False, today, today) == ("replay", today)
    assert select_issue_mode(True, today, today) == ("live", today)
    assert select_issue_mode(True, last, today) == ("replay", last)
    assert select_issue_mode(True, today, today, "2025-12-20") == ("replay", date(2025, 12, 20))


def test_dm_and_undefined_exceedance_scores():
    y = np.arange(80) % 20 + 20.0
    dates = pd.date_range("2025-07-01", periods=80)
    result = dm_test(dates, y, y + 0.1, y + 5, 3)
    assert result["p_value"] < 0.01 and result["statistic"] < 0
    assert dm_test(dates, y, y, y, 3)["p_value"] == 1
    frame = pd.DataFrame({"y": y, "prediction": y, "persistence": y + 1})
    score = scores(frame)
    assert score["pod"] is None and score["far"] is None and score["csi"] is None
    assert score["skill_vs_persistence"] == 1


@pytest.mark.django_db
def test_forecast_api_read_only_replay_and_date_validation():
    city = CityFactory(slug="hyderabad")
    run = AnalysisRun.objects.create(
        started_at=timezone.now(),
        name="phase4",
        status="success",
        data_start=date(2024, 1, 1),
        data_end=date(2025, 12, 31),
    )
    version = ForecastModelVersion.objects.create(
        city=city,
        horizon=1,
        algorithm="persistence",
        mlflow_run_id="test",
        registry_name="test",
        registry_version="1",
        training_start=date(2024, 1, 1),
        training_end=date(2025, 10, 1),
        available_from=date(2025, 12, 1),
        analysis_run=run,
        cohort="all_stations",
    )
    Forecast.objects.create(
        city=city,
        issued_for_date=date(2025, 12, 31),
        target_date=date(2026, 1, 1),
        horizon=1,
        point=20,
        lower80=15,
        upper80=25,
        lower95=10,
        upper95=30,
        aqi_category="good",
        mode="replay",
        model_version=version,
        top_drivers=[{"feature": "pm_t", "value": 20, "shap_value": 1}],
    )
    client = APIClient()
    url = "/api/forecast/hyderabad/latest/"
    response = client.get(url)
    assert response.status_code == 200
    assert response.data["forecasts"][0]["mode"] == "replay"
    assert response.data["forecasts"][0]["top_drivers"][0]["feature"] == "pm_t"
    assert client.post(url, {}).status_code == 405
    assert client.get("/api/forecast/missing/latest/").status_code == 404
    assert client.get("/api/forecast/hyderabad/history/?start=2026-01-01&end=2026-01-01").data[
        "forecasts"
    ]
    assert (
        client.get("/api/forecast/hyderabad/history/?start=2026-01-02&end=2026-01-01").status_code
        == 400
    )
    assert (
        client.get("/api/forecast/hyderabad/history/?start=wrong&end=2026-01-01").status_code == 400
    )
