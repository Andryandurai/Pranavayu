import json
import time
import uuid
from datetime import UTC, date, datetime, timedelta

from django.conf import settings

from apps.ingest.base import Source
from apps.ingest.units import number, to_utc
from apps.warehouse.models import City, WeatherObservation

VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "surface_pressure",
    "cloud_cover",
    "precipitation",
    "shortwave_radiation",
    "boundary_layer_height",
)


class OpenMeteoSource(Source):
    slug = "openmeteo"
    name = "Open-Meteo ERA5 historical weather"
    url = "https://open-meteo.com/en/docs/historical-weather-api"
    licence = (
        "CC BY 4.0; attribute Open-Meteo, ECMWF and Copernicus. Free API for non-commercial use."
    )
    access_method = "api"

    @staticmethod
    def windows(start=None, end=None):
        start = date.fromisoformat(start or "2015-01-01")
        latest = datetime.now(UTC).date() - timedelta(days=5)
        end = min(date.fromisoformat(end) if end else latest, latest)
        if start > end:
            raise ValueError("Weather start must be no later than ERA5's latest available date")
        while start <= end:
            stop = min(end, date(start.year, 12, 31))
            yield start, stop
            start = stop + timedelta(days=1)

    def download(self, start=None, end=None, **options):
        for city in City.objects.all():
            for first, last in self.windows(start, end):
                try:
                    self.fetch(city, first, last)
                except Exception as exc:
                    self.fail_asset(f"{city.slug}:{first}:{last}", exc)

    def fetch(self, city, first, last):
        result = self.download_asset(
            "https://archive-api.open-meteo.com/v1/archive",
            f"openmeteo/{city.slug}/{first}_{last}.json",
            params={
                "latitude": city.location.y,
                "longitude": city.location.x,
                "start_date": first.isoformat(),
                "end_date": last.isoformat(),
                "hourly": ",".join(VARIABLES),
                "timezone": "UTC",
                "wind_speed_unit": "ms",
                "models": "era5",
            },
            metadata={
                "city": city.slug,
                "model": "era5",
                "timezone": "UTC",
                "boundary_layer_height": "ERA5 archive variable, metres; null when missing",
            },
        )
        if not self.cache.last_cache_hit:
            time.sleep(settings.INGEST_REQUEST_PAUSE)
        return result

    def load_payload(self, payload, city, asset):
        hourly = payload.get("hourly", {})
        units = payload.get("hourly_units", {})
        if units.get("wind_speed_10m", "m/s") != "m/s":
            raise ValueError("Weather response wind units are not m/s")
        times = hourly.get("time", [])
        if not times or payload.get("utc_offset_seconds", 0) != 0:
            raise ValueError("Weather response must contain hourly UTC timestamps")
        self.run.rows_fetched += len(times)
        objects, metadata = [], {}

        def value(key, index):
            data = hourly.get(key, [])
            return number(data[index]) if index < len(data) else None

        for index, instant in enumerate(times):
            observed_at = to_utc(instant, UTC)
            identifier = uuid.uuid5(
                uuid.NAMESPACE_URL, f"{self.slug}:era5:{city.slug}:{observed_at.isoformat()}"
            )
            temp = value("temperature_2m", index)
            rh = value("relative_humidity_2m", index)
            wind = value("wind_speed_10m", index)
            pressure = value("surface_pressure", index)
            cloud = value("cloud_cover", index)
            precipitation = value("precipitation", index)
            radiation = value("shortwave_radiation", index)
            blh = value("boundary_layer_height", index)
            invalid = (temp is not None and not -100 <= temp <= 70) or (
                rh is not None and not 0 <= rh <= 100
            )
            invalid |= any(
                v is not None and v < 0
                for v in (wind, pressure, cloud, precipitation, radiation, blh)
            )
            objects.append(
                WeatherObservation(
                    id=identifier,
                    observed_at=observed_at,
                    city=city,
                    location=city.location,
                    source=self.source,
                    temperature_c=temp if temp is None or -100 <= temp <= 70 else None,
                    relative_humidity=rh if rh is None or 0 <= rh <= 100 else None,
                    wind_speed_ms=wind if wind is None or wind >= 0 else None,
                    wind_dir_deg=(
                        value("wind_direction_10m", index) % 360
                        if value("wind_direction_10m", index) is not None
                        else None
                    ),
                    boundary_layer_height_m=blh if blh is None or blh >= 0 else None,
                    surface_pressure_hpa=pressure if pressure is None or pressure > 0 else None,
                    solar_radiation_wm2=radiation if radiation is None or radiation >= 0 else None,
                    total_cloud_cover=cloud / 100
                    if cloud is not None and 0 <= cloud <= 100
                    else None,
                    precipitation_mm=precipitation
                    if precipitation is None or precipitation >= 0
                    else None,
                )
            )
            metadata[identifier] = {
                "dew_point_2m_c": value("dew_point_2m", index),
                "grid_latitude": payload.get("latitude"),
                "grid_longitude": payload.get("longitude"),
                "model": "era5",
                "invalid_values": bool(invalid),
            }
            if len(objects) >= settings.INGEST_BATCH_SIZE:
                self.insert_observations(WeatherObservation, objects, "weather", asset, metadata)
                objects, metadata = [], {}
        self.insert_observations(WeatherObservation, objects, "weather", asset, metadata)

    def load(self, start=None, end=None, **options):
        for city in City.objects.all():
            for first, last in self.windows(start, end):
                try:
                    path, asset = self.fetch(city, first, last)
                    self.load_payload(json.loads(path.read_text()), city, asset)
                except Exception as exc:
                    self.fail_asset(f"{city.slug}:{first}:{last}", exc)
