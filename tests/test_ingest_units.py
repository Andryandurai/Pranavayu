from datetime import UTC, datetime, timedelta

import pytest

from apps.ingest.quality import aggregate_quarters, flag_readings
from apps.ingest.units import (
    IST,
    concentration,
    humidity_from_dewpoint,
    number,
    to_utc,
    wind_from_components,
)


def test_ist_and_explicit_offsets():
    assert to_utc("01-01-2019 00:00") == datetime(2018, 12, 31, 18, 30, tzinfo=UTC)
    assert to_utc("2024-01-01T00:00:00.000000+0000").hour == 0
    assert to_utc("2024-01-01T00:00:00Z").tzinfo == UTC


@pytest.mark.parametrize(
    "value,unit,code,expected",
    [
        (10, "µg/m³", "pm25", 10),
        (0.01, "mg/m3", "pm25", 10),
        (1000, "µg/m³", "co", 1),
        (1, "mg/m³", "co", 1),
        (10, "ppb", "no2", 18.8045),
        (1, "ppm", "co", 1.1449),
    ],
)
def test_units(value, unit, code, expected):
    assert concentration(value, unit, code) == pytest.approx(expected, rel=0.001)


def test_unsupported_units_and_missing_values():
    for value in (None, "NA", "NaN", "Infinity", ""):
        assert number(value) is None
    with pytest.raises(ValueError):
        concentration(10, "AQI", "pm25")
    with pytest.raises(ValueError):
        concentration(10, "ppb", "pm25")


@pytest.mark.parametrize("count,expected", [(2, None), (3, 20), (4, 25)])
def test_quarter_aggregation_requires_three_distinct_slots(count, expected):
    first = datetime(2024, 1, 1, tzinfo=IST)
    samples = [(first + timedelta(minutes=i * 15), (i + 1) * 10) for i in range(count)]
    hour, value, _, flag = aggregate_quarters(samples, IST)[0]
    assert hour == to_utc(first)
    assert value == expected
    assert flag == ("missing" if count < 3 else "ok")
    assert aggregate_quarters([samples[0]] * 4, IST)[0][1] is None


def test_quarter_off_grid_and_invalid_values():
    with pytest.raises(ValueError):
        aggregate_quarters([("2024-01-01T00:05:00Z", 1)])
    result = aggregate_quarters([("2024-01-01T00:00:00Z", -1), ("2024-01-01T00:15:00Z", 1)])
    assert result[0][1] is None and result[0][3] == "negative"


def test_wind_and_humidity_derivation():
    assert wind_from_components(3, 4) == pytest.approx((5, 216.86989765))
    assert wind_from_components(0, 0) == (0, None)
    assert wind_from_components(None, 1) == (None, None)
    assert humidity_from_dewpoint(25, 25) == pytest.approx(100)
    assert humidity_from_dewpoint(25, 15) == pytest.approx(53.85, abs=0.1)
    assert humidity_from_dewpoint(None, 15) is None


def row(value, code="pm25", hour=0):
    return {
        "station_id": 1,
        "code": code,
        "observed_at": datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=hour),
        "value": value,
        "raw_value": value,
    }


@pytest.mark.parametrize(
    "value,code,flag",
    [
        (-1, "pm25", "negative"),
        (None, "pm25", "missing"),
        (1001, "pm25", "outlier"),
        (2001, "pm10", "outlier"),
        (1000, "pm25", "ok"),
        (2000, "pm10", "ok"),
    ],
)
def test_flags_preserve_raw_and_outliers(value, code, flag):
    sample = row(value, code)
    flag_readings([sample])
    assert sample["quality_flag"] == flag
    assert sample["raw_value"] == value
    assert sample["value"] == (None if flag == "negative" else value)


def test_stuck_flags_first_five_hours_and_breaks_on_gaps():
    samples = [row(20, hour=i) for i in range(7)]
    assert {r["quality_flag"] for r in flag_readings(samples)} == {"stuck"}
    samples = [row(20, hour=i) for i in [0, 1, 2, 4, 5, 6]]
    assert {r["quality_flag"] for r in flag_readings(samples)} == {"ok"}


def test_pm25_pm10_comparison_and_flag_priority():
    samples = [row(20), row(10, "pm10")]
    assert flag_readings(samples)[0]["quality_flag"] == "pm25_gt_pm10"
    samples = [row(1001), row(10, "pm10")]
    assert flag_readings(samples)[0]["quality_flag"] == "outlier"
