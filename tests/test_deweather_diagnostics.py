import hashlib
import json
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
import responses
from sklearn.ensemble import RandomForestRegressor

from apps.analytics.diagnostic_data import cached_quarters, correct_published_clock
from apps.analytics.model_diagnostics import (
    lag_correlations,
    pooled_normalise,
    week_folds,
    week_labels,
)
from apps.ingest.models import DataSource
from apps.warehouse.models import City
from tests.factories import StationFactory


@pytest.fixture(autouse=True)
def no_external_http():
    with responses.RequestsMock():
        yield


def test_lag_identifies_a_known_positive_and_negative_timestamp_offset():
    rng = np.random.default_rng(123)
    index = pd.date_range("2024-01-01", periods=240, freq="h", tz="UTC")
    signal = pd.Series(rng.normal(size=len(index)), index=index)
    for offset in [-7, 5]:
        wind = signal.copy()
        wind.index = pd.to_datetime(wind.index.asi8 + offset * 3600 * 1_000_000_000, utc=True)
        result = lag_correlations(signal, wind)
        peak = result.loc[result.correlation.idxmax()]
        assert peak.lag_hours == offset
        assert peak.correlation == pytest.approx(1)


def test_verified_opencity_wall_clock_converts_to_utc_without_shifting_other_sources():
    times = pd.Series(pd.to_datetime(["2024-01-01T00:00:00Z"] * 2, utc=True))
    converted = correct_published_clock(times, ["opencity", "cpcb-ccr"])
    assert converted.iloc[0] == pd.Timestamp("2023-12-31T18:30:00Z")
    assert converted.iloc[0].tz_convert("Asia/Kolkata").hour == 0
    assert converted.iloc[1] == times.iloc[1]
    assert times.iloc[0] == pd.Timestamp("2024-01-01T00:00:00Z")


def test_week_cv_never_leaks_ist_weeks_or_boundary_embargo():
    times = pd.Series(
        pd.date_range("2019-01-01", periods=24 * 120, freq="h", tz="UTC").append(
            pd.date_range("2024-01-01", periods=24 * 120, freq="h", tz="UTC")
        )
    )
    weeks = week_labels(times)
    seen = []
    for train, test in week_folds(times):
        assert not set(weeks.iloc[train]) & set(weeks.iloc[test])
        assert set(times.iloc[train].dt.year) == {2019, 2024}
        seen.extend(test)
        for week in set(weeks.iloc[test]):
            first = pd.Timestamp(week, tz="Asia/Kolkata").tz_convert("UTC").to_pydatetime()
            last = first + timedelta(days=7)
            assert not (
                (times.iloc[train] >= first - timedelta(hours=24))
                & (times.iloc[train] < last + timedelta(hours=24))
            ).any()
    assert sorted(seen) == list(range(len(times)))
    again = list(week_folds(times))
    assert all(np.array_equal(a[1], b[1]) for a, b in zip(again, week_folds(times), strict=True))
    with pytest.raises(ValueError, match="gap"):
        list(week_folds(pd.Series(pd.date_range("2021-01-01", periods=200, freq="h", tz="UTC"))))


def test_pooled_weather_same_seed_and_draws_reproduce_for_both_periods():
    rng = np.random.default_rng(12)
    x = pd.DataFrame(
        dict(
            trend=np.tile(np.arange(80), 2),
            temperature=rng.normal(size=160),
            period=np.repeat([0, 1], 80),
        )
    ).astype(np.float32)
    y = x.temperature * 3 + x.period * 20 + x.trend * 0.1
    model = RandomForestRegressor(n_estimators=12, max_depth=6, random_state=42).fit(
        x.to_numpy(), y
    )
    first = pooled_normalise(model, x, x)
    second = pooled_normalise(model, x, x)
    assert np.array_equal(first[0], second[0])
    assert np.array_equal(first[1], second[1])
    # Compare the exact grouping optimisation against direct shared donor predictions.
    donors = x.to_numpy()[np.random.default_rng(42).integers(len(x), size=300)].copy()
    for i in [0, 79, 80, 159]:
        direct = donors.copy()
        direct[:, 0], direct[:, 2] = x.iloc[i, 0], x.iloc[i, 2]
        assert first[0][i] == pytest.approx(model.predict(direct).mean())
    with pytest.raises(ValueError, match="300"):
        pooled_normalise(model, x, x, n_samples=299)


@pytest.mark.django_db
def test_ist_hour_reconstruction_uses_quarters_across_utc_hour_boundary(tmp_path, settings):
    from django.core.management import call_command

    call_command("seed_reference", verbosity=0)
    city = City.objects.get(slug="delhi")
    source = DataSource.objects.create(slug="opencity", name="Fixture OpenCity")
    StationFactory(city=city, source=source, external_id="site_fixture")
    settings.RAW_DATA_ROOT = tmp_path
    path = tmp_path / "opencity" / "delhi" / "quarters.csv"
    path.parent.mkdir(parents=True)
    lines = ["Timestamp,Station ID,PM2.5,PM10"]
    for i in range(8):
        time = datetime(2024, 1, 1, tzinfo=UTC) + timedelta(minutes=15 * i)
        lines.append(f"{time.isoformat()},site_fixture,{i + 1},100")
    path.write_text("\n".join(lines))
    manifest = dict(
        path="opencity/delhi/quarters.csv",
        size_bytes=path.stat().st_size,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        metadata={},
    )
    path.with_name(path.name + ".manifest.json").write_text(json.dumps(manifest))
    frame, files = cached_quarters(city)
    valid = frame[frame.quality_flag == "ok"]
    assert len(valid) == 1
    assert valid.iloc[0].observed_at == datetime(2024, 1, 1, 0, 30, tzinfo=UTC)
    assert valid.iloc[0].value == 4.5
    assert files[0]["bytes"] == path.stat().st_size
