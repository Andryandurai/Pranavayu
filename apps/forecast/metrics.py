import numpy as np
import pandas as pd
from scipy.stats import t


def aqi_category(value):
    if not np.isfinite(value) or value < 0:
        raise ValueError("PM2.5 must be finite and nonnegative")
    return ("good", "satisfactory", "moderate", "poor", "very_poor", "severe")[
        int(np.searchsorted([30, 60, 90, 120, 250], value, side="left"))
    ]


def conformal_radius(errors, alpha):
    values = np.sort(np.abs(np.asarray(errors, dtype=float)))
    values = values[np.isfinite(values)]
    rank = int(np.ceil((len(values) + 1) * (1 - alpha)))
    if rank > len(values) or rank < 1:
        raise ValueError("Calibration sample too small for requested conformal coverage")
    return float(values[rank - 1])


def dm_test(dates, observed, prediction, persistence, horizon):
    losses = (np.asarray(prediction) - observed) ** 2 - (np.asarray(persistence) - observed) ** 2
    n = len(losses)
    if np.max(np.abs(losses)) < 1e-12:
        return {"statistic": 0.0, "p_value": 1.0, "hac_lag": max(7, horizon - 1), "loss": "squared"}
    centered = pd.Series(losses - losses.mean(), index=pd.to_datetime(dates))
    centered = centered.reindex(pd.date_range(centered.index.min(), centered.index.max()))
    lag = max(7, horizon - 1)
    variance = float(np.nanmean(centered.to_numpy() ** 2))
    for k in range(1, lag + 1):
        paired = pd.concat([centered, centered.shift(k)], axis=1).dropna()
        if len(paired):
            variance += (
                2 * (1 - k / (lag + 1)) * float((paired.iloc[:, 0] * paired.iloc[:, 1]).sum() / n)
            )
    if variance <= 0:
        return {
            "statistic": None,
            "p_value": None,
            "hac_lag": lag,
            "reason": "nonpositive HAC variance",
        }
    correction = ((n + 1 - 2 * horizon + horizon * (horizon - 1) / n) / n) ** 0.5
    stat = float(losses.mean() / np.sqrt(variance / n) * correction)
    return {
        "statistic": stat,
        "p_value": float(2 * t.sf(abs(stat), df=n - 1)),
        "hac_lag": lag,
        "loss": "squared",
    }


def scores(frame, prediction="prediction"):
    y = frame.y.to_numpy()
    p = frame[prediction].to_numpy()
    base = frame.persistence.to_numpy()
    error = p - y
    rmse = float(np.sqrt(np.mean(error**2)))
    base_rmse = float(np.sqrt(np.mean((base - y) ** 2)))
    hit = int(((p > 60) & (y > 60)).sum())
    miss = int(((p <= 60) & (y > 60)).sum())
    false = int(((p > 60) & (y <= 60)).sum())
    return {
        "n": len(y),
        "rmse": rmse,
        "mae": float(np.mean(np.abs(error))),
        "skill_vs_persistence": float(1 - rmse / base_rmse) if base_rmse else None,
        "aqi_category_accuracy": float(
            np.mean([aqi_category(v) == aqi_category(w) for v, w in zip(y, p, strict=True)])
        ),
        "nmb_percent": float(100 * error.sum() / y.sum()) if y.sum() else None,
        "mean_bias": float(error.mean()),
        "observed_exceedances": hit + miss,
        "forecast_exceedances": hit + false,
        "hits": hit,
        "misses": miss,
        "false_alarms": false,
        "pod": hit / (hit + miss) if hit + miss else None,
        "far": false / (hit + false) if hit + false else None,
        "csi": hit / (hit + miss + false) if hit + miss + false else None,
    }
