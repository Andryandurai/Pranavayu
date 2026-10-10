from datetime import date, timedelta

import numpy as np
import pytest
from django.utils import timezone

from apps.analytics.models import AnalysisRun
from apps.forecast.data import make_features
from apps.forecast.models import Forecast, ForecastModelVersion, ForecastWeather
from apps.ingest.models import RawAsset
from tests.factories import CityFactory, IngestionRunFactory
from tests.test_forecasting import feature_fixture


@pytest.mark.django_db
def test_actual_issue_pipeline_replays_without_key(monkeypatch, tmp_path):
    import joblib
    from django.test import override_settings

    from apps.forecast import operations
    from apps.forecast.estimators import TREE_GRID, Baseline, TreeModel

    monkeypatch.delenv("OPENAQ_API_KEY", raising=False)
    hourly, daily, records = feature_fixture()
    city = CityFactory(slug="hyderabad")
    run = AnalysisRun.objects.create(
        started_at=timezone.now(),
        name="phase4",
        status="success",
        data_start=date(2024, 1, 1),
        data_end=date(2024, 2, 1),
    )
    ingest = IngestionRunFactory()
    asset = RawAsset.objects.create(
        source=ingest.source, ingestion_run=ingest, path="fixture", sha256="a" * 64, size_bytes=1
    )
    monkeypatch.setattr(operations, "load_hourly", lambda slug: (hourly, {"fixture": True}))
    monkeypatch.setattr(
        operations, "operational_hourly", lambda *a: pytest.fail("No key: live lookup forbidden")
    )
    issued = date(2024, 2, 1)
    for horizon in (1, 2, 3):
        for r in records:
            ForecastWeather.objects.create(
                city=city,
                source=ingest.source,
                ingestion_run=ingest,
                asset=asset,
                mode="archive",
                horizon=horizon,
                issued_for_date=r["issued_for_date"],
                target_date=r["issued_for_date"] + timedelta(days=horizon),
                lead_days=horizon + 1,
                available_by=r["available_by"],
                features=r["features"],
                hours=24,
            )
        rows = make_features(daily, records, horizon)
        training = rows[rows.y.notna()].copy()
        calibration = training.copy()
        calibration["y"] = calibration.pm_t + np.linspace(-4, 4, len(calibration))
        path = tmp_path / f"h{horizon}.joblib"
        model = Baseline("persistence").fit(training)
        quantiles = {
            str(a): TreeModel(TREE_GRID[0], a).fit(training) for a in (0.025, 0.1, 0.9, 0.975)
        }
        joblib.dump(
            {
                "model": model,
                "quantiles": quantiles,
                "calibration": calibration,
                "background": training,
                "chosen": "persistence",
                "selection": {"radius80": 3.0, "radius95": 4.0},
            },
            path,
        )
        ForecastModelVersion.objects.create(
            city=city,
            horizon=horizon,
            algorithm="persistence",
            mlflow_run_id="fixture",
            registry_name="fixture",
            registry_version="1",
            training_start=date(2024, 1, 1),
            training_end=date(2024, 1, 10),
            available_from=date(2024, 1, 11),
            artifact_path=str(path),
            analysis_run=run,
            cohort="all_stations",
        )
    with override_settings(FORECAST_CITIES=(city.slug,)):
        result = operations.issue_forecasts()
    assert len(result) == 3
    assert all(r["mode"] == "replay" and r["issued_for_date"] == str(issued) for r in result)
    assert Forecast.objects.filter(mode="replay", issued_for_date=issued).count() == 3
    assert all(len(f.top_drivers) == 5 for f in Forecast.objects.all())
    # A keyed source with only today's observations still lacks the required lags.
    import pandas as pd

    completed = timezone.localdate() - timedelta(days=1)
    fresh_hourly = pd.DataFrame(
        {
            "observed_at": pd.date_range(
                pd.Timestamp(completed, tz="Asia/Kolkata"), periods=24, freq="h"
            ),
            "value": np.repeat(20.0, 24),
            "station_count": np.repeat(1, 24),
        }
    )
    monkeypatch.setenv("OPENAQ_API_KEY", "fixture-only-not-used-for-network")
    monkeypatch.setattr(operations, "operational_hourly", lambda *a: fresh_hourly)
    with override_settings(FORECAST_CITIES=(city.slug,)):
        fallback = operations.issue_forecasts()
    assert all(r["mode"] == "replay" and r["fallback_reason"] for r in fallback)
    assert Forecast.objects.count() == 3


def test_sarimax_state_never_assimilates_future_target_labels():
    from apps.forecast.estimators import SarimaxModel

    _, daily, records = feature_fixture()
    rows = make_features(daily, records, 3)
    train = rows[rows.y.notna()].iloc[:12]
    model = SarimaxModel((1, 0, 0), 3).fit(train)
    issued = rows.index[-2]
    test = rows.loc[[issued]]
    before = model.predict(test, rows)
    assert np.isfinite(before).all()
    contaminated = rows.copy()
    contaminated.loc[contaminated.target_date > issued, "y"] = 99999
    np.testing.assert_allclose(model.predict(test, contaminated), before, rtol=0, atol=1e-12)


def test_live_state_uses_frozen_calibration_and_preserves_measured_labels():
    import pandas as pd

    from apps.forecast.estimators import SarimaxModel
    from apps.forecast.operations import observed_history, operational_intervals

    class StateModel(SarimaxModel):
        def predict(self, rows, history=None):
            assert rows.index.min() == pd.Timestamp("2026-10-10")
            return np.repeat(20.0, len(rows))

    class Quantile:
        def __init__(self, value):
            self.value = value

        def predict(self, rows):
            return np.repeat(self.value, len(rows))

    calibration = pd.DataFrame({"y": np.linspace(15, 25, 60)})
    test = pd.DataFrame(index=[pd.Timestamp("2026-10-10")])
    bundle = {
        "model": StateModel((1, 0, 0), 3),
        "calibration": calibration,
        "selection": {"radius80": 3.0, "radius95": 5.0},
        "quantiles": {
            "0.025": Quantile(10),
            "0.1": Quantile(12),
            "0.9": Quantile(28),
            "0.975": Quantile(30),
        },
    }
    result, info = operational_intervals(bundle, test, pd.DataFrame())
    assert result["lower80"][0] == 17 and result["upper80"][0] == 23
    assert result["lower95"][0] == 15 and result["upper95"][0] == 25
    assert info["calibration_n"] == 60
    _, daily, records = feature_fixture()
    rows = make_features(daily, records, 3).drop(pd.Timestamp("2024-01-20"))
    history = observed_history(daily, rows, 3)
    assert history.loc["2024-01-20", "y"] == daily.loc["2024-01-23", "value"]
    assert pd.isna(history.loc["2024-01-20", "pm_t"])


def test_daily_pm_refresh_includes_current_day_and_ten_day_lag_history(monkeypatch):
    from datetime import UTC, datetime
    from types import SimpleNamespace

    from apps.forecast import operations

    instant = datetime(2026, 10, 10, 18, 5, tzinfo=UTC)
    called = {}

    class Source:
        def execute(self, action, **kwargs):
            called.update(action=action, **kwargs)
            return SimpleNamespace(status="success")

    monkeypatch.setattr(operations, "OpenAQSource", Source)
    monkeypatch.setattr(operations.timezone, "now", lambda: instant)
    assert operations.refresh_live_pm().status == "success"
    assert called == {
        "action": "load",
        "start": (instant - timedelta(days=10)).isoformat(),
        "end": instant.isoformat(),
    }


@pytest.mark.django_db
def test_daily_forecast_schedules_refresh_pm_before_issue_cutoff():
    from django_celery_beat.models import PeriodicTask

    from apps.forecast.tasks import configure_schedules

    configure_schedules()
    configure_schedules()
    tasks = PeriodicTask.objects.filter(
        name__in=["Forecast PM inputs daily", "Forecast weather daily", "PM2.5 forecasts daily"]
    )
    assert tasks.count() == 3
    expected = {
        "Forecast PM inputs daily": ("23", "35"),
        "Forecast weather daily": ("23", "40"),
        "PM2.5 forecasts daily": ("0", "10"),
    }
    for task in tasks:
        assert (task.crontab.hour, task.crontab.minute) == expected[task.name]
        assert str(task.crontab.timezone) == "Asia/Kolkata"
