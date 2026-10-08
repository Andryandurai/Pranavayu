from collections import defaultdict
from datetime import UTC, timedelta

from .units import MOLAR_MASS, MOLAR_VOLUME_L, concentration, number, to_utc

QUALITY_RULE_VERSION = "phase3a-positive-flatline-with-quarter-evidence-v1"


def aggregate_quarters(samples, timezone=UTC):
    """Distinct 15-minute slots; preserve missing/invalid raw values without filling."""
    hours = defaultdict(dict)
    for timestamp, value in samples:
        local = to_utc(timestamp, timezone).astimezone(timezone)
        if local.minute not in (0, 15, 30, 45) or local.second:
            raise ValueError("Quarter-hour input contains off-grid timestamps")
        hour = local.replace(minute=0, second=0, microsecond=0)
        hours[hour][local.minute] = number(value)
    results = []
    for hour, slots in sorted(hours.items()):
        reported = [value for value in slots.values() if value is not None]
        valid = [value for value in reported if value >= 0]
        raw = sum(reported) / len(reported) if reported else None
        if len(valid) >= 3:
            value, flag = sum(valid) / len(valid), "ok"
        else:
            value, flag = None, "negative" if any(value < 0 for value in reported) else "missing"
        results.append((hour.astimezone(to_utc(hour).tzinfo), value, raw, flag))
    return results


def quarter_variation(samples, timezone=UTC):
    """Whether reported valid quarter values vary inside a nominal source hour."""
    hours = defaultdict(dict)
    for timestamp, value in samples:
        local = to_utc(timestamp, timezone).astimezone(timezone)
        hours[local.replace(minute=0, second=0, microsecond=0)][local.minute] = number(value)
    return {
        hour: len({v for v in slots.values() if v is not None and v >= 0}) > 1
        for hour, slots in hours.items()
    }


def flag_readings(rows):
    """Flag whole constant runs, including their first five hours. Never discard outliers."""
    groups = defaultdict(list)
    pairs = defaultdict(dict)

    def mark_streak(streak):
        # Zero can be a reporting floor. Equal rounded hourly means alone do
        # not establish a frozen response if their source quarters varied.
        if len(streak) < 6 or streak[0]["value"] is None or streak[0]["value"] <= 0:
            return
        if any(item.get("quarter_varies", False) for item in streak):
            return
        for item in streak:
            if item["quality_flag"] == "ok":
                item["quality_flag"] = "stuck"

    for row in rows:
        raw, value = number(row.get("raw_value")), number(row.get("value"))
        row["raw_value"], row["value"] = raw, value
        existing = row.get("quality_flag", "ok")
        maximum = MOLAR_MASS.get(row["code"], 0) / MOLAR_VOLUME_L * 1e9
        if row["code"] == "co":
            maximum /= 1000
        impossible = row["code"] in MOLAR_MASS and value is not None and value > maximum
        if (
            existing == "negative"
            or impossible
            or (raw is not None and raw < 0)
            or (value is not None and value < 0)
        ):
            row["quality_flag"], row["value"] = "negative", None
        elif value is None:
            row["quality_flag"] = "missing"
        elif (row["code"] == "pm25" and value > 1000) or (row["code"] == "pm10" and value > 2000):
            row["quality_flag"] = "outlier"
        else:
            row["quality_flag"] = "ok"
        groups[(row["station_id"], row["code"])].append(row)
        pairs[(row["station_id"], row["observed_at"])][row["code"]] = row
    for group in groups.values():
        streak = []
        for row in sorted(group, key=lambda item: item["observed_at"]):
            same = (
                streak
                and row["value"] is not None
                and row["value"] == streak[-1]["value"]
                and not row.get("quarter_varies", False)
                and not streak[-1].get("quarter_varies", False)
            )
            consecutive = streak and row["observed_at"] - streak[-1]["observed_at"] == timedelta(
                hours=1
            )
            if not (same and consecutive):
                mark_streak(streak)
                streak = []
            streak.append(row)
        mark_streak(streak)
    for pair in pairs.values():
        pm25, pm10 = pair.get("pm25"), pair.get("pm10")
        if pm25 and pm10 and pm25["value"] is not None and pm10["value"] is not None:
            if pm25["value"] > pm10["value"] and pm25["quality_flag"] == "ok":
                pm25["quality_flag"] = "pm25_gt_pm10"
    return rows


def normalize_reading(raw, unit, code):
    raw = number(raw)
    return {"raw_value": raw, "value": concentration(raw, unit, code), "code": code}
