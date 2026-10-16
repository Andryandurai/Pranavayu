import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from rest_framework.test import APIClient

from apps.forecast.data import raw_daily
from apps.forecast.estimators import Baseline
from apps.forecast.serving import PersistenceUnavailable, persistence_input, served_forecast
from tests.test_forecast_serving_policy import LOSERS
from tests.test_forecast_serving_policy import stored_forecast as stored_forecast

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / "tests/fixtures/forecast_persistence_equivalence.json").read_text())
PAIRS = sorted({(r["city"], r["horizon"]) for r in FIXTURE["comparisons"]})
MISSING = "No forecast: input data missing for this issue date."


def stored_hourly(city, settings, tmp_path):
    hourly = pd.DataFrame(FIXTURE["hourly"][city]["rows"])
    hourly["observed_at"] = pd.to_datetime(hourly.observed_at, utc=True)
    suffix = "panel_hourly" if city == "bengaluru" else "hourly"
    path = tmp_path / "data/results/8" / f"{city}_{suffix}.pkl"
    path.parent.mkdir(parents=True, exist_ok=True)
    hourly.to_pickle(path)
    settings.BASE_DIR = tmp_path
    return hourly


@pytest.mark.parametrize(("city", "horizon"), PAIRS)
def test_evaluated_and_served_persistence_agree_on_fixed_stored_issue_dates(
    city, horizon, settings, tmp_path
):
    hourly = stored_hourly(city, settings, tmp_path)
    daily = raw_daily(hourly)
    samples = [
        row for row in FIXTURE["comparisons"] if row["city"] == city and row["horizon"] == horizon
    ]
    assert [row["issue_date"] for row in samples] == FIXTURE["sample_issue_dates"]
    for row in samples:
        day = pd.Timestamp(row["issue_date"])
        evaluated = float(Baseline("persistence").predict(daily.loc[[day]])[0])
        forecast = SimpleNamespace(
            city=SimpleNamespace(slug=city),
            horizon=horizon,
            issued_for_date=day.date(),
            mode="replay",
            feature_provenance={},
        )
        served = served_forecast(forecast)
        assert served["forecast_method"] == "persistence"
        np.testing.assert_allclose(served["point"], evaluated, rtol=0, atol=1e-10)
        np.testing.assert_allclose(
            served["point"], row["evaluated_persistence"], rtol=0, atol=1e-10
        )
        # New issuance captures exactly the evaluation's pm_t, with no horizon shift.
        forecast.feature_provenance = {"persistence_value": float(daily.loc[day, "pm_t"])}
        assert persistence_input(forecast) == evaluated


def test_day_with_only_seventeen_hours_does_not_carry_an_earlier_day_forward(settings, tmp_path):
    hourly = stored_hourly("bengaluru", settings, tmp_path)
    day = FIXTURE["sample_issue_dates"][1]
    local = hourly.observed_at.dt.tz_convert("Asia/Kolkata").dt.strftime("%Y-%m-%d")
    short = pd.concat([hourly[local != day], hourly[local == day].iloc[:17]])
    path = tmp_path / "data/results/8/bengaluru_panel_hourly.pkl"
    short.to_pickle(path)
    assert pd.isna(raw_daily(short).loc[day, "value"])
    forecast = SimpleNamespace(
        city=SimpleNamespace(slug="bengaluru"),
        issued_for_date=date.fromisoformat(day),
        mode="replay",
        feature_provenance={},
    )
    with pytest.raises(PersistenceUnavailable, match="input data missing"):
        persistence_input(forecast)


def test_missing_input_api_has_actionable_message(stored_forecast, settings, tmp_path):
    forecast = stored_forecast(LOSERS[0])
    forecast.feature_provenance = {}
    forecast.save(update_fields=["feature_provenance"])
    settings.BASE_DIR = tmp_path
    response = APIClient().get(f"/api/forecast/{forecast.city.slug}/latest/")
    assert response.status_code == 503
    assert str(response.data["detail"]).startswith(MISSING)
    assert "the losing model is not served" in str(response.data["detail"])


@pytest.mark.django_db
def test_dashboard_has_explicit_read_only_availability_check(client, django_assert_num_queries):
    with django_assert_num_queries(0):
        response = client.get("/dashboard/")
    html = response.content.decode()
    assert 'id="check-serving"' in html
    assert 'id="serving-status" role="status"' in html
    assert "Choose a city and check input availability." in html
    assert "serving-status.js" in html
