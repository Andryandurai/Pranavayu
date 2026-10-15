"""Published stability and wind-profile tables; SI inputs throughout."""

import numpy as np

# EPA ISC3 Volume II, EPA-454/B-95-003b, printed p.1-5, Table 1-1.
# https://gaftp.epa.gov/aqmg/SCRAM/models/other/isc3/isc3v2.pdf
WIND_EXPONENTS = {
    "rural": dict(zip("ABCDEF", [0.07, 0.07, 0.10, 0.15, 0.35, 0.55], strict=True)),
    "urban": dict(zip("ABCDEF", [0.15, 0.15, 0.20, 0.25, 0.30, 0.30], strict=True)),
}


def stability_class(wind_ms, solar_wm2, cloud_fraction, daytime):
    """Measured-radiation SRDT daytime / Turner cloud-table nighttime hybrid.

    EPA Meteorological Monitoring Guidance (2000), Table 6-7, printed p.6-16
    supplies daytime thresholds 925/675/175 W/m². Night uses Turner (1970)
    Table 3-1: >=half cloud versus clear. Cloud ceiling and nighttime delta-T
    are unavailable, so this is explicitly an approximation, not full Turner.
    """
    if not np.isfinite(wind_ms) or wind_ms < 0:
        raise ValueError("Wind must be finite and nonnegative")
    if daytime:
        if solar_wm2 is None or not np.isfinite(solar_wm2) or solar_wm2 < 0:
            raise ValueError("Daytime solar radiation is required")
        band = int(np.searchsorted([2, 3, 5, 6], wind_ms, side="right"))
        radiation = (
            0 if solar_wm2 >= 925 else 1 if solar_wm2 >= 675 else 2 if solar_wm2 >= 175 else 3
        )
        return ["AABD", "ABCD", "BBCD", "CCDD", "CDDD"][band][radiation]
    if cloud_fraction is None or not np.isfinite(cloud_fraction) or not 0 <= cloud_fraction <= 1:
        raise ValueError("Nighttime cloud fraction is required")
    if cloud_fraction >= 0.875:  # Turner overcast: neutral, day or night.
        return "D"
    if wind_ms >= 5:
        return "D"
    if cloud_fraction >= 0.5:
        return "E" if wind_ms < 3 else "D"
    return "F" if wind_ms < 3 else "E"


def wind_at_height(wind_ms, height_m, stability, environment="urban"):
    """ISC3 Eq.1-6 at release height, with the published minimum wind1m/s."""
    exponent = WIND_EXPONENTS[environment][stability]
    return np.maximum(1.0, wind_ms * (np.maximum(height_m, 0.0) / 10.0) ** exponent)


def fallback_mixing_height(stability, daytime):
    """Illustrative, source-backed anchors, NOT local observed/climatological BLH.

    CDM2 User Guide Table5, printed p.15: A=1.5L, B/C/Dday=L,
    Dnight=(L+Lmin)/2, E/F=Lmin. Adopt L=1500m from Turner Problem6
    and Lmin=500m from EPA Screening Procedures Fig4-19, printed p.4-62 (a screening
    example, not a recommended Indian nighttime climatology).
    This transfer assumption must be exposed in every affected result.
    """
    if stability == "A":
        return 2250.0
    if stability in "EF":
        return 500.0
    return 1000.0 if stability == "D" and not daytime else 1500.0
