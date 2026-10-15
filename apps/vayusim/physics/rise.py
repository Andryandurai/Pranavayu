"""ISC3 Vol II, printed pp.1-6--1-11, Briggs rise, Eqs.1-7--1-29.

https://gaftp.epa.gov/aqmg/SCRAM/models/other/isc3/isc3v2.pdf
No building-downwash/terrain/chemistry or regulatory-model equivalence.
"""

import numpy as np

G = 9.80616  # ISC3 Eq.1-8, not a fitted coefficient.


def effective_height(
    x,
    height_m,
    diameter_m,
    exit_velocity_ms,
    exit_temperature_k,
    ambient_temperature_k,
    wind_ms,
    stability,
):
    x = np.maximum(np.asarray(x, dtype=float), 0.0)
    v, d, ts, ta, u = (
        exit_velocity_ms,
        diameter_m,
        exit_temperature_k,
        ambient_temperature_k,
        wind_ms,
    )
    v, d, ts, ta, u, height_m = np.broadcast_arrays(v, d, ts, ta, u, height_m)
    enabled = (v > 0) & (d > 0)
    tip = np.where(v / u < 1.5, np.maximum(0.0, height_m + 2 * d * (v / u - 1.5)), height_m)
    fb = np.maximum(0.0, G * v * d * d * (ts - ta) / (4 * ts))
    fm = v * v * d * d * ta / (4 * ts)
    beta = 1 / 3 + u / np.where(v > 0, v, 1.0)
    stable = stability in "EF"
    if stable:
        s = G / ta * (0.020 if stability == "E" else 0.035)
        crossover = 0.019582 * ts * v * np.sqrt(s)
        final_b = 2.6 * np.cbrt(fb / (u * s))
        final_m = np.minimum(1.5 * np.cbrt(fm / (u * np.sqrt(s))), 3 * d * v / u)
        buoyancy = np.minimum(1.6 * np.cbrt(fb) * x ** (2 / 3) / u, final_b)
        capped = np.minimum(x * np.sqrt(s) / u, np.pi / 2)
        momentum = np.minimum(
            np.cbrt(3 * fm * np.sin(capped) / (beta * beta * u * np.sqrt(s))), final_m
        )
    else:
        crossover = np.where(
            fb < 55,
            0.0297 * ts * v ** (1 / 3) * d ** (2 / 3),
            0.00575 * ts * v ** (2 / 3) * d ** (1 / 3),
        )
        final_b = np.where(fb < 55, 21.425 * fb**0.75, 38.71 * fb**0.6) / u
        final_m = 3 * d * v / u
        buoyancy = np.minimum(1.6 * np.cbrt(fb) * x ** (2 / 3) / u, final_b)
        momentum = np.minimum(np.cbrt(3 * fm * x / (beta * beta * u * u)), final_m)
    rise = np.where((ts - ta >= crossover) & (fb > 0), buoyancy, momentum)
    return np.where(enabled, tip + rise, height_m)
