import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.contrib.gis.geos import Point
from django.db import connection
from django.db.models import Q

from apps.ingest.base import Source, insert_reading_batch
from apps.ingest.quality import QUALITY_RULE_VERSION, flag_readings
from apps.ingest.units import concentration, number, to_utc
from apps.warehouse.models import City, Pollutant, Reading, Station

# A public demonstration token published by the data publisher, not a user secret.
# https://airquality.xkdr.org/#docs
REGISTRY_URL = "https://airquality.xkdr.org/v1/stations"
PUBLIC_HEADERS = {"Authorization": "Bearer aqi_demo_wbf92Qx21zX-Wa_Tg8Dx1nXe"}
COORDINATE_REVISION = "1fbf3fa5bebf5195ca095e43c4a9a27a666b944c"
COORDINATE_SNAPSHOT = (
    f"https://huggingface.co/datasets/Zeel/C1/resolve/{COORDINATE_REVISION}/station_data.csv"
)
ALIASES = {
    "pm2.5": "pm25",
    "pm25": "pm25",
    "pm10": "pm10",
    "no2": "no2",
    "so2": "so2",
    "co": "co",
    "ozone": "o3",
    "o3": "o3",
    "nh3": "nh3",
}


def name_key(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())


def csv_rows(path):
    # Some OpenCity exports use CR CR LF; csv handles the extra blank lines.
    with path.open(encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


class AirSource(Source):
    def registry(self):
        path, asset = self.download_asset(
            REGISTRY_URL,
            "cpcb/station-registry.json",
            headers=PUBLIC_HEADERS,
            metadata={"publisher": "XKDR Forum", "licence": "CC BY 4.0"},
        )
        self.run.params["station_registry_asset"] = asset.pk
        records = json.loads(path.read_text())["data"]
        if any(number(r["latitude"]) is None or number(r["longitude"]) is None for r in records):
            supplement_path, supplement = self.download_asset(
                COORDINATE_SNAPSHOT,
                "cpcb/contributed-station-coordinates.csv",
                metadata={
                    "publisher": "Zeel/C1 contributed station metadata",
                    "revision": COORDINATE_REVISION,
                    "licence": "Not declared by this metadata compilation",
                    "coordinates_independently_surveyed": False,
                },
            )
            coordinates = defaultdict(list)
            for row in csv_rows(supplement_path):
                coordinates[name_key(row["station"].split(" - ", 1)[0])].append(row)
            for record in records:
                if (
                    number(record["latitude"]) is not None
                    and number(record["longitude"]) is not None
                ):
                    continue
                candidates = coordinates.get(
                    name_key(record["station_name"].split(" - ", 1)[0]), []
                )
                unique = {(number(r["latitude"]), number(r["longitude"])) for r in candidates}
                if len(unique) == 1 and None not in next(iter(unique)):
                    record["latitude"], record["longitude"] = next(iter(unique))
                    record["coordinate_asset"] = supplement.pk
            self.run.params["coordinate_supplement_asset"] = supplement.pk
        return records

    def station(self, name, external_id, city, latitude=None, longitude=None, registry=None):
        if not name:
            raise ValueError(f"Station name missing for {external_id}; provide export metadata")
        if registry is not None and (latitude is None or longitude is None):
            candidates = [r for r in registry if r["source"] == "cpcb_caaqm"]
            # A known site ID is authoritative. Name aliases can be shared by
            # distinct IDs (for example Pusa); only fall back when ID is absent.
            matches = [r for r in candidates if r["station_id"] == external_id]
            if not matches:
                matches = [r for r in candidates if name_key(r["station_name"]) == name_key(name)]
            if len(matches) != 1:
                raise ValueError(f"No unambiguous coordinates for station {external_id}: {name}")
            latitude, longitude = matches[0]["latitude"], matches[0]["longitude"]
            if matches[0].get("coordinate_asset"):
                self.run.params.setdefault("coordinate_supplement_stations", {})[external_id] = {
                    "asset": matches[0]["coordinate_asset"],
                    "name": name,
                    "quality": "published contributed snapshot; location needs independent review",
                }
        latitude, longitude = number(latitude), number(longitude)
        if (
            latitude is None
            or longitude is None
            or not (-90 <= latitude <= 90 and -180 <= longitude <= 180)
        ):
            raise ValueError(f"Missing/invalid station coordinates: {name}")
        point = Point(longitude, latitude, srid=4326)
        match = Station.objects.filter(
            source=self.source, name__iexact=name, location__distance_lte=(point, 100)
        ).first()
        if match:
            return match
        station, _ = Station.objects.update_or_create(
            source=self.source,
            external_id=external_id,
            defaults={
                "name": name,
                "city": city,
                "location": point,
                "operator": name.rsplit(" - ", 1)[-1] if " - " in name else "",
            },
        )
        return station

    def insert_readings(self, rows, asset):
        """Flag an entire station series before batching so six-hour streaks span batches."""
        pollutants = dict(Pollutant.objects.values_list("code", "id"))
        self.run.params["quality_rule_version"] = QUALITY_RULE_VERSION
        intervals = defaultdict(list)
        for row in rows:
            intervals[(row["station_id"], row["code"])].append(row["observed_at"])
        context = []
        for (station_id, code), dates in intervals.items():
            first, last = min(dates), max(dates)
            matches = (
                Reading.objects.filter(station_id=station_id, pollutant_id=pollutants[code])
                .filter(
                    Q(observed_at__gte=first - timedelta(hours=5), observed_at__lt=first)
                    | Q(observed_at__gt=last, observed_at__lte=last + timedelta(hours=5))
                )
                .values("station_id", "observed_at", "value", "raw_value", "quality_flag")
            )
            context.extend({**r, "code": code, "previous_flag": r["quality_flag"]} for r in matches)
        flag_readings(rows + context)
        changed = [
            r
            for r in context
            if r["quality_flag"] == "stuck" and r["previous_flag"] in {"ok", "pm25_gt_pm10"}
        ]
        if changed:
            # Quality metadata may improve when an adjacent file arrives; values
            # and the first ingestion provenance remain immutable on conflict.
            placeholders = ",".join(["(%s,%s,%s::timestamptz,%s)"] * len(changed))
            parameters = [
                v
                for r in changed
                for v in (
                    r["station_id"],
                    pollutants[r["code"]],
                    r["observed_at"],
                    r["quality_flag"],
                )
            ]
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""UPDATE warehouse_reading r SET quality_flag=v.flag
                    FROM (VALUES {placeholders}) v(station,pollutant,observed,flag)
                    WHERE r.station_id=v.station AND r.pollutant_id=v.pollutant
                      AND r.observed_at=v.observed""",
                    parameters,
                )
            self.run.params["existing_flags_revised"] = self.run.params.get(
                "existing_flags_revised", 0
            ) + len(changed)
        self.run.params.setdefault("raw_assets", [])
        if asset.pk not in self.run.params["raw_assets"]:
            self.run.params["raw_assets"].append(asset.pk)
        inserted_count = 0
        for offset in range(0, len(rows), settings.INGEST_BATCH_SIZE):
            inserted = insert_reading_batch(
                rows[offset : offset + settings.INGEST_BATCH_SIZE], pollutants, self.run.pk
            )
            inserted_count += len(inserted)
            self.run.rows_inserted += len(inserted)
            self.run.rows_flagged += sum(r[3] != "ok" for r in inserted)
            self.run.save(
                update_fields=[
                    "rows_fetched",
                    "rows_inserted",
                    "rows_flagged",
                    "params",
                    "updated_at",
                ]
            )
        by_station = defaultdict(list)
        for row in rows:
            by_station[row["station_id"]].append(row["observed_at"])
        for pk, dates in by_station.items():
            station = Station.objects.get(pk=pk)
            station.first_seen = min(
                [min(dates)] + ([station.first_seen] if station.first_seen else [])
            )
            station.last_seen = max(
                [max(dates)] + ([station.last_seen] if station.last_seen else [])
            )
            station.save(update_fields=["first_seen", "last_seen", "updated_at"])
        self.event(
            "asset_loaded",
            path=asset.path,
            hourly_pollutant_rows=len(rows),
            inserted=inserted_count,
        )
        return inserted_count

    def load_csv(self, path, *, registry=None, quarter=False, metadata=None):
        from apps.ingest.quality import aggregate_quarters, quarter_variation

        path, asset = self.local_asset(path, **(metadata or {}))
        cities = {name_key(c.name): c for c in City.objects.all()}
        registry_by_id = {r["station_id"]: r for r in registry or []}
        stations = {}
        series = defaultdict(list)
        rows = []
        source_units = self.run.params.setdefault("raw_units", {})
        for raw in csv_rows(path):
            lowered = {key.lower().strip(): value for key, value in raw.items() if key}
            timestamp = (
                lowered.get("timestamp")
                or lowered.get("collected_at")
                or lowered.get("from date")
                or lowered.get("datetime")
                or lowered.get("date")
            )
            if not timestamp:
                continue
            external_id = (
                lowered.get("station id") or lowered.get("station_id") or lowered.get("site_id")
            )
            name = (
                lowered.get("station name")
                or lowered.get("station_name")
                or (metadata or {}).get("station_name")
            )
            if not external_id:
                external_id = hashlib.sha256((name or str(path)).encode()).hexdigest()[:32]
            info = registry_by_id.get(external_id, {})
            name = name or info.get("station_name")
            city_name = lowered.get("city") or info.get("city_name") or (metadata or {}).get("city")
            city = cities.get(name_key(city_name or ""))
            if city is None:
                continue
            if external_id not in stations:
                stations[external_id] = self.station(
                    name,
                    external_id,
                    city,
                    lowered.get("latitude"),
                    lowered.get("longitude"),
                    registry,
                )
            station = stations[external_id]
            instant = to_utc(timestamp)
            values = []
            if "parameter_name" in lowered or "pollutant" in lowered:
                parameter = lowered.get("parameter_name") or lowered["pollutant"]
                code = ALIASES.get(parameter.lower())
                if code:
                    values.append(
                        (
                            code,
                            lowered.get("unit", "mg/m³" if code == "co" else "µg/m³"),
                            lowered.get("value"),
                        )
                    )
            else:
                for header, value in raw.items():
                    if header is None:
                        continue
                    label = header.strip().lower()
                    code = ALIASES.get(label.split(" (")[0])
                    if code:
                        unit = (
                            header.split("(", 1)[1].rstrip(")")
                            if "(" in header
                            else ("mg/m³" if code == "co" else "µg/m³")
                        )
                        values.append((code, unit, value))
            for code, unit, value in values:
                source_units[f"{station.pk}:{code}"] = unit
                raw_value = number(value)
                self.run.rows_fetched += 1
                if quarter:
                    series[(station.pk, code, unit)].append((instant, raw_value))
                else:
                    rows.append(
                        {
                            "station_id": station.pk,
                            "code": code,
                            "observed_at": instant,
                            "value": concentration(raw_value, unit, code),
                            "raw_value": raw_value,
                        }
                    )
        for (station_id, code, unit), samples in series.items():
            variations = quarter_variation(samples)
            for instant, value, raw_mean, flag in aggregate_quarters(samples):
                rows.append(
                    {
                        "station_id": station_id,
                        "code": code,
                        "observed_at": instant,
                        "value": concentration(value, unit, code),
                        "raw_value": raw_mean,
                        "quality_flag": flag,
                        "quarter_varies": variations.get(instant, False),
                    }
                )
        if not rows:
            self.event(
                "asset_unusable",
                path=str(path),
                reason="No seeded-city concentration rows; AQI matrices are not concentrations",
            )
            return 0
        return self.insert_readings(rows, asset)
