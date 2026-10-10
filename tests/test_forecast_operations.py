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
