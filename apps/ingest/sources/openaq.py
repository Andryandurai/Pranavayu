import json
import os
from datetime import UTC, datetime, timedelta

from apps.ingest.base import SourceUnavailable
from apps.ingest.units import concentration, number, to_utc
from apps.warehouse.models import City

from .air import ALIASES, AirSource


class OpenAQSource(AirSource):
    slug = "openaq"
    name = "OpenAQ"
    url = "https://api.openaq.org/v3"
    licence = "Original data provider licences apply; attribute OpenAQ and providers."
    access_method = "api"

    def pages(self, endpoint, relative, params, key):
        page = 1
        while True:
            path, asset = self.download_asset(
                f"{self.url}/{endpoint}",
                f"openaq/{relative}-p{page}.json",
                params={**params, "page": page, "limit": 1000},
                headers={"X-API-Key": key},
                refresh=endpoint == "locations",
            )
            payload = json.loads(path.read_text())
            if not isinstance(payload.get("results"), list):
                raise ValueError("OpenAQ response lacks its results array")
            results = payload["results"]
            yield results, asset
            if len(results) < 1000:
                break
            page += 1

    def load(self, start=None, end=None, **options):
        key = os.environ.get("OPENAQ_API_KEY")
        if not key:
            raise SourceUnavailable("skipped: no key")
        end = end or datetime.now(UTC).isoformat()
        start = start or (datetime.now(UTC) - timedelta(days=1)).isoformat()
        start, end = to_utc(start).isoformat(), to_utc(end).isoformat()
        self.run.params.update({"start": start, "end": end, "raw_units": {}})
        for city in City.objects.all():
            try:
                for locations, _ in self.pages(
                    "locations",
                    f"locations-{city.slug}",
                    {
                        "coordinates": f"{city.location.y},{city.location.x}",
                        "radius": 25000,
                        "iso": "IN",
                    },
                    key,
                ):
                    for location in locations:
                        coords = location["coordinates"]
                        station = self.station(
                            location["name"],
                            str(location["id"]),
                            city,
                            coords["latitude"],
                            coords["longitude"],
                        )
                        rows = []
                        assets = []
                        for sensor in location.get("sensors", []):
                            parameter = sensor["parameter"]
                            code = ALIASES.get(parameter["name"].lower())
                            if code not in {"pm25", "pm10", "no2", "so2", "co", "o3"}:
                                continue
                            for hours, asset in self.pages(
                                f"sensors/{sensor['id']}/hours",
                                f"{sensor['id']}-{to_utc(start).date()}-{to_utc(end).date()}",
                                {"datetime_from": start, "datetime_to": end},
                                key,
                            ):
                                assets.append(asset)
                                for hour in hours:
                                    unit = hour.get("parameter", parameter).get(
                                        "units", parameter["units"]
                                    )
                                    raw = number(hour.get("value"))
                                    instant = hour["period"]["datetimeFrom"]["utc"]
                                    rows.append(
                                        {
                                            "station_id": station.pk,
                                            "code": code,
                                            "observed_at": to_utc(instant),
                                            "value": concentration(raw, unit, code),
                                            "raw_value": raw,
                                        }
                                    )
                                    self.run.rows_fetched += 1
                                    self.run.params["raw_units"][f"{station.pk}:{code}"] = unit
                        if rows:
                            self.run.params.setdefault("raw_assets", []).extend(
                                a.pk for a in assets
                            )
                            self.insert_readings(rows, assets[0])
            except Exception as exc:
                self.fail_asset(city.slug, exc)
