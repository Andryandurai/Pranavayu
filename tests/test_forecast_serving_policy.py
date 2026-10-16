import json
import re
from datetime import date
from pathlib import Path

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.analytics.models import AnalysisRun
from apps.forecast.metrics import aqi_category
from apps.forecast.models import Forecast, ForecastModelVersion
from apps.forecast.serving import (
    PersistenceUnavailable,
    load_serving_policy,
    persistence_input,
    serving_policy,
)
from tests.factories import CityFactory

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / "tests/fixtures/forecast_serving_phase4.json").read_text())
LOSERS = [r for r in FIXTURE["forecasts"] if r["city"] != "delhi"]


def test_policy_table_matches_phase4_losing_list_exactly():
    report = (ROOT / "docs/results/PHASE4.md").read_text(encoding="utf-8")
    comparison = report.split("## Model comparisons")[1].split("## Issued-policy")[0]
    losing = set()
    for line in comparison.splitlines():
        if re.match(r"\| [a-z]+ \| [123] \|", line):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if float(cells[9]) > float(cells[3]):
                losing.add((cells[0], int(cells[1])))
    config = load_serving_policy()
    actual = {(c, int(h)) for c, horizons in config["policies"].items() for h in horizons}
    assert len(losing) == 9
    assert actual == losing == {(r["city"], r["horizon"]) for r in LOSERS}
    assert config["source"].startswith("docs/results/PHASE4.md#")


@pytest.fixture
def stored_forecast(db):
    def create(row):
        city = CityFactory(slug=row["city"])
        issued = date.fromisoformat(row["issued_for_date"])
        target = date.fromisoformat(row["target_date"])
        run = AnalysisRun.objects.create(
            name="phase4",
            status="success",
            started_at=timezone.now(),
            data_start=issued,
            data_end=target,
        )
        version = ForecastModelVersion.objects.create(
            city=city,
            horizon=row["horizon"],
            algorithm=row["algorithm"],
            mlflow_run_id="stored-fixture",
            registry_name="stored-fixture",
            registry_version="1",
            training_start=issued,
            training_end=issued,
            available_from=issued,
            analysis_run=run,
            cohort="fixed_panel" if city.slug == "bengaluru" else "all_stations",
        )
        return Forecast.objects.create(
            city=city,
            issued_for_date=issued,
            target_date=target,
            horizon=row["horizon"],
            point=row["prediction"],
            lower80=row["lower80"],
            upper80=row["upper80"],
            lower95=row["lower95"],
            upper95=row["upper95"],
            aqi_category=aqi_category(row["prediction"]),
            mode="replay",
            model_version=version,
            feature_provenance={"persistence_value": row["pm_t"], "fixture_source": row["source"]},
        )

    return create


@pytest.mark.parametrize("row", LOSERS, ids=lambda r: f"{r['city']}-h{r['horizon']}")
@pytest.mark.parametrize("endpoint", ["latest/", "history/?start=2025-12-31&end=2025-12-31"])
def test_api_serves_persistence_for_all_nine_without_rewriting_stored_values(
    row, endpoint, stored_forecast
):
    original = stored_forecast(row)
    before = Forecast.objects.filter(pk=original.pk).values().get()
    response = APIClient().get(f"/api/forecast/{row['city']}/{endpoint}")
    assert response.status_code == 200
    served = response.data["forecasts"][0]
    assert served["point"] == row["pm_t"]
    assert served["forecast_method"] == "persistence"
    assert served["policy_source"] == "phase4-persistence-v1"
    assert served["fallback_reason"] == "model_loses_to_persistence_phase4"
    assert served["fallback_used"] is True
    assert served["algorithm"] == "persistence"
    assert served["aqi_category"] == aqi_category(row["pm_t"])
    assert served["top_drivers"] == []
    assert all(served[k] is None for k in ["lower80", "upper80", "lower95", "upper95"])
    assert "No fallback interval coverage is claimed" in served["interval_policy"]["serving_note"]
    assert Forecast.objects.filter(pk=original.pk).values().get() == before


@pytest.mark.parametrize("endpoint", ["latest/", "history/?start=2025-12-31&end=2025-12-31"])
def test_delhi_next_day_retains_model_forecast(endpoint, stored_forecast):
    # PHASE4.md Model comparisons: Delhi h1 policy RMSE 29.417 < persistence 33.668.
    row = next(r for r in FIXTURE["forecasts"] if r["city"] == "delhi")
    stored_forecast(row)
    served = APIClient().get(f"/api/forecast/delhi/{endpoint}").data["forecasts"][0]
    assert served["point"] == row["prediction"] != row["pm_t"]
    assert served["forecast_method"] == "model"
    assert served["policy_source"] == "phase4-persistence-v1"
    assert served["fallback_reason"] is None
    assert served["fallback_used"] is False
    assert served["algorithm"] == row["algorithm"]
    assert all(served[k] == row[k] for k in ["lower80", "upper80", "lower95", "upper95"])


def test_non_override_model_path_may_itself_have_selected_a_baseline():
    assert serving_policy("bengaluru", 2)["forecast_method"] == "model"
    assert not serving_policy("bengaluru", 2)["fallback_used"]


def test_fallback_omits_original_model_bounds_from_provenance(stored_forecast):
    forecast = stored_forecast(LOSERS[0])
    forecast.feature_provenance.update(
        original_interval_bounds={key: LOSERS[0][key] for key in ("lower80", "upper80")},
        interval_policy={"choices": {}},
    )
    forecast.save(update_fields=["feature_provenance"])
    served = APIClient().get(f"/api/forecast/{forecast.city.slug}/latest/").data["forecasts"][0]
    assert "original_interval_bounds" not in served["feature_provenance"]
    assert "interval_policy" not in served["feature_provenance"]
    forecast.refresh_from_db()
    assert "original_interval_bounds" in forecast.feature_provenance


def test_missing_persistence_is_not_replaced_with_losing_model(
    stored_forecast, monkeypatch, tmp_path
):
    from django.conf import settings

    forecast = stored_forecast(LOSERS[0])
    forecast.feature_provenance = {}
    forecast.save(update_fields=["feature_provenance"])
    monkeypatch.setattr(settings, "BASE_DIR", tmp_path)
    response = APIClient().get(f"/api/forecast/{forecast.city.slug}/latest/")
    assert response.status_code == 503
    assert "losing model is not served" in str(response.data)


def test_legacy_replay_uses_issue_day_fixed_panel_not_target_day(
    stored_forecast, monkeypatch, tmp_path
):
    import pandas as pd
    from django.conf import settings

    from apps.forecast import serving

    row = LOSERS[0]
    forecast = stored_forecast(row)
    forecast.feature_provenance = {}
    path = tmp_path / "data/results/8/bengaluru_panel_hourly.pkl"
    path.parent.mkdir(parents=True)
    path.touch()
    monkeypatch.setattr(settings, "BASE_DIR", tmp_path)
    observed = []

    def daily(path_string, modified, size):
        observed.append(path_string)
        return {
            pd.Timestamp(forecast.issued_for_date): row["pm_t"],
            pd.Timestamp(forecast.target_date): row["prediction"],
        }

    monkeypatch.setattr(serving, "_archived_daily", daily)
    assert persistence_input(forecast) == row["pm_t"]
    assert observed == [str(path)]
    forecast.mode = "live"
    with pytest.raises(PersistenceUnavailable):
        persistence_input(forecast)


@pytest.mark.django_db
def test_dashboard_shows_current_serving_separately_from_historical_gap(
    client, django_assert_num_queries
):
    with django_assert_num_queries(0):
        response = client.get("/dashboard/")
    text = response.content.decode()
    assert text.count("forecast_method: persistence") == 9
    assert text.count("forecast_method: model") == 12
    assert text.count("policy_source: phase4-persistence-v1") == 21
    assert "Historical Phase 7 snapshot · before this fix" in text
