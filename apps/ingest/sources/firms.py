import csv
import os
import uuid
from datetime import UTC, datetime, timedelta
from io import StringIO

from django.conf import settings
from django.contrib.gis.geos import Point

from apps.ingest.base import Source, SourceUnavailable
from apps.ingest.units import number, to_utc
from apps.warehouse.models import FireDetection


class FIRMSsource(Source):
    slug = "nasa-firms"
    name = "NASA FIRMS"
    url = "https://firms.modaps.eosdis.nasa.gov/"
    licence = "NASA Earth science data policy; acknowledge FIRMS and MODIS/VIIRS providers."
    access_method = "api"

    def load_csv(self, path):
        path, asset = self.local_asset(path)
        objects, metadata = [], {}
        reader = csv.DictReader(StringIO(path.read_text(encoding="utf-8-sig")))
        required = {"latitude", "longitude", "acq_date", "acq_time"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(
                "FIRMS response is not a detection CSV (check key/product availability)"
            )
        for row in reader:
            latitude, longitude = number(row.get("latitude")), number(row.get("longitude"))
            if (
                latitude is None
                or longitude is None
                or not -90 <= latitude <= 90
                or not -180 <= longitude <= 180
            ):
                raise ValueError("FIRMS CSV contains invalid coordinates")
            time = row["acq_time"].zfill(4)
            instant = to_utc(f"{row['acq_date']}T{time[:2]}:{time[2:]}:00+00:00")
            satellite = row.get("satellite", "")
            product = row.get("instrument", "") + ":" + row.get("version", "")
            identifier = uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"firms:{product}:{satellite}:{latitude}:{longitude}:{instant.isoformat()}",
            )
            frp = number(row.get("frp"))
            flagged = frp is not None and frp < 0
            self.run.rows_fetched += 1
            objects.append(
                FireDetection(
                    id=identifier,
                    detected_at=instant,
                    location=Point(longitude, latitude, srid=4326),
                    satellite=f"{satellite} {row.get('instrument', '')}".strip(),
                    confidence=row.get("confidence", ""),
                    frp=None if flagged else frp,
                    source=self.source,
                )
            )
            metadata[identifier] = {"product": product, "raw_frp": frp, "invalid_values": flagged}
            if len(objects) >= settings.INGEST_BATCH_SIZE:
                self.insert_observations(FireDetection, objects, "fire", asset, metadata)
                objects, metadata = [], {}
        self.insert_observations(FireDetection, objects, "fire", asset, metadata)

    def load(self, start=None, end=None, **options):
        key = os.environ.get("FIRMS_MAP_KEY")
        if not key:
            raise SourceUnavailable("skipped: no key")
        today = datetime.now(UTC).date()
        first = datetime.fromisoformat(start).date() if start else today - timedelta(days=1)
        last = datetime.fromisoformat(end).date() if end else today
        for product in ("VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "MODIS_NRT"):
            current = first
            while current <= last:
                days = min(5, (last - current).days + 1)
                try:
                    path, _ = self.download_asset(
                        f"{self.url}api/area/csv/{key}/{product}/{settings.FIRMS_BBOX}/{days}/{current}",
                        f"firms/{product}/{current}-{days}.csv",
                        metadata={"product": product, "bbox": settings.FIRMS_BBOX},
                    )
                    self.load_csv(path)
                except Exception as exc:
                    self.fail_asset(f"{product}:{current}", exc)
                current += timedelta(days=days)
        self.load_archives()

    def load_archives(self):
        for path in sorted(self.cache.root.glob("firms/*.csv")):
            self.load_csv(path)
