"""Versioned presentation policy; never updates historical forecasts or fits models."""

import json
import math
from functools import lru_cache
from pathlib import Path

from rest_framework.exceptions import APIException

CONFIG_PATH = Path(__file__).with_name("config") / "serving_policy_v1.json"


@lru_cache(maxsize=1)
def load_serving_policy():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if config["default_method"] != "model" or any(
        method != "persistence" or horizon not in {"1", "2", "3"}
        for horizons in config["policies"].values()
        for horizon, method in horizons.items()
    ):
        raise ValueError("Invalid forecast serving policy")
    return config


def serving_policy(city, horizon):
    config = load_serving_policy()
    method = config["policies"].get(city, {}).get(str(horizon), config["default_method"])
    fallback = method == "persistence"
    return {
        "forecast_method": method,
        "policy_source": config["version"],
        "fallback_used": fallback,
        "fallback_reason": config["fallback_reason"] if fallback else None,
    }


class PersistenceUnavailable(APIException):
    status_code = 503
    default_detail = "Issue-day persistence input unavailable; the losing model is not served."
    default_code = "persistence_input_unavailable"


@lru_cache(maxsize=16)
def _archived_daily(path_string, modified_ns, size):
    """Read the retained Phase 4 cohort, not a current or target-day observation."""
    import pandas as pd

    from .data import raw_daily

    hourly = pd.read_pickle(path_string)
    return raw_daily(hourly)["value"].to_dict()


def persistence_input(forecast):
    from django.conf import settings

    value = forecast.feature_provenance.get("persistence_value")
    if value is None:
        # Historical rows predate captured persistence_value. Only replay can use
        # this frozen cohort; never substitute archive observations for live data.
        if forecast.mode != "replay":
            raise PersistenceUnavailable()
        suffix = "panel_hourly" if forecast.city.slug == "bengaluru" else "hourly"
        path = settings.BASE_DIR / "data/results/8" / f"{forecast.city.slug}_{suffix}.pkl"
        try:
            stat = path.stat()
            daily = _archived_daily(str(path), stat.st_mtime_ns, stat.st_size)
            import pandas as pd

            value = daily.get(pd.Timestamp(forecast.issued_for_date))
        except (OSError, ValueError, KeyError) as exc:
            raise PersistenceUnavailable() from exc
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise PersistenceUnavailable() from exc
    if not math.isfinite(value) or value < 0:
        raise PersistenceUnavailable()
    return value


def served_forecast(forecast):
    """One policy shared by latest/history, Ask's serializer and home cards."""
    from .metrics import aqi_category

    result = serving_policy(forecast.city.slug, forecast.horizon)
    if result["fallback_used"]:
        point = persistence_input(forecast)
        result.update(
            point=point,
            algorithm="persistence",
            aqi_category=aqi_category(point),
            top_drivers=[],
            feature_provenance={
                key: value
                for key, value in forecast.feature_provenance.items()
                if key not in {"original_interval_bounds", "interval_policy"}
            },
            lower80=None,
            upper80=None,
            lower95=None,
            upper95=None,
            interval_policy={
                "choices": {},
                "serving_note": "Original model intervals do not assess this persistence override. "
                "No fallback interval coverage is claimed; see unchanged Phase 4 evaluation.",
            },
        )
    return result
