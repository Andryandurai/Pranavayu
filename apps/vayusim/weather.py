from datetime import UTC, timedelta
from zoneinfo import ZoneInfo

from rest_framework.exceptions import ValidationError

from apps.warehouse.models import Reading, WeatherObservation

from .physics.meteorology import fallback_mixing_height, stability_class

IST = ZoneInfo("Asia/Kolkata")
FALLBACK_CITATIONS = [
    {
        "url": "https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=9101EO4F.TXT",
        "section": "CDM2 Table5, printed p15 (class relationships)",
    },
    {
        "url": "https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=9101GKEZ.TXT",
        "section": "Turner AP26 Problem6, L=1500m illustrative inversion",
    },
    {
        "url": "https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=2000F86J.TXT",
        "section": "EPA Screening Procedures Fig4-19, p4-62, L=500m example",
    },
]


def hour_bounds(moment):
    start = moment.astimezone(IST).replace(minute=0, second=0, microsecond=0)
    return start.astimezone(UTC), (start + timedelta(hours=1)).astimezone(UTC)


def weather_for(inputs, city):
    flags = [
        "Stability approximation: SRDT measured-radiation day / Turner cloud-table night; "
        "ceiling and delta-T unavailable"
    ]
    if inputs["weather_mode"] == "manual":
        weather = dict(inputs["weather"])
        provenance = {"mode": "manual", "label": "User-supplied meteorology; not observations"}
    else:
        start, end = hour_bounds(inputs["datetime"])
        midpoint = start + (end - start) / 2
        observation = (
            WeatherObservation.objects.filter(city=city, observed_at=midpoint)
            .select_related("source")
            .first()
        )
        if observation is None:
            raise ValidationError(
                {
                    "weather": (
                        "No observation at this IST hour's UTC midpoint; "
                        "choose an archived hour or manual mode"
                    )
                }
            )
        required = [
            observation.wind_speed_ms,
            observation.wind_dir_deg,
            observation.temperature_c,
            observation.solar_radiation_wm2,
            observation.total_cloud_cover,
        ]
        if any(x is None for x in required):
            raise ValidationError(
                {"weather": "Required wind, temperature, solar or cloud observation is null"}
            )
        weather = {
            "wind_speed_ms": required[0],
            "wind_direction_deg": required[1],
            "temperature_k": required[2] + 273.15,
            "solar_radiation_wm2": required[3],
            "cloud_fraction": required[4],
            "daytime": observation.solar_radiation_wm2 > 0,
        }
        if (
            observation.boundary_layer_height_m is not None
            and observation.boundary_layer_height_m > 0
        ):
            weather["mixing_height_m"] = observation.boundary_layer_height_m
        provenance = {
            "mode": "real",
            "observation_id": str(observation.id),
            "observed_at_utc": midpoint.isoformat(),
            "ist_hour_start": start.astimezone(IST).isoformat(),
            "source": observation.source.slug,
            "label": "City weather grid point; uniform over the scenario",
        }
    weather["stability_class"] = stability_class(
        weather["wind_speed_ms"],
        weather["solar_radiation_wm2"],
        weather["cloud_fraction"],
        weather["daytime"],
    )
    if "mixing_height_m" not in weather:
        weather["mixing_height_m"] = fallback_mixing_height(
            weather["stability_class"], weather["daytime"]
        )
        flags.append(
            "Missing boundary-layer height: illustrative stability-based fallback; "
            "not Indian climatology or measured BLH"
        )
        provenance["mixing_height"] = {
            "observed": False,
            "citations": FALLBACK_CITATIONS,
            "assumption": "CDM2 class ratios using illustrative L=1500m and Lmin=500m anchors",
        }
    else:
        provenance["mixing_height"] = {
            "observed": inputs["weather_mode"] == "real",
            "value_m": weather["mixing_height_m"],
            "label": "Warehouse observation" if inputs["weather_mode"] == "real" else "User input",
        }
    return weather, provenance, flags


def background_stations(city, moment, centre, distance_km=25):
    from django.db.models import Avg, Count, Q
    from pyproj import Geod

    start, end = hour_bounds(moment)
    rows = (
        Reading.objects.filter(
            station__city=city,
            station__source__slug__in=["cpcb-ccr", "opencity"],
            pollutant__code="pm25",
            observed_at__gte=start,
            observed_at__lt=end,
            quality_flag="ok",
            value__isnull=False,
        )
        .filter(
            Q(station__analysis_eligibility__isnull=True)
            | Q(station__analysis_eligibility__excluded_from_spatial=False)
        )
        .values("station_id", "station__name", "station__location")
        .annotate(mean_value=Avg("value"), samples=Count("value"))
    )
    result = []
    for row in rows:
        point = row["station__location"]
        if point is None:
            continue
        _, _, distance = Geod(ellps="WGS84").inv(*centre, point.x, point.y)
        if distance <= distance_km * 1000:
            result.append(
                {
                    "station_id": row["station_id"],
                    "name": row["station__name"],
                    "location": [point.x, point.y],
                    "distance_km": distance / 1000,
                    "value_ugm3": row["mean_value"],
                    "samples": row["samples"],
                }
            )
    return {
        "label": "measured total (all sources)",
        "unit": "µg/m³",
        "ist_hour": start.astimezone(IST).isoformat(),
        "stations": sorted(result, key=lambda r: r["distance_km"]),
        "note": "Independent context only; never added to the modelled increment",
    }
