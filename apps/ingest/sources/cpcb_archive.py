import json
import time
from datetime import date, timedelta

from django.conf import settings

from apps.ingest.base import SourceUnavailable
from apps.warehouse.models import City

from .air import PUBLIC_HEADERS, AirSource


class CPCBArchiveSource(AirSource):
    slug = "cpcb-ccr"
    name = "CPCB CCR"
    url = "https://airquality.cpcb.gov.in/ccr/"
    licence = "CPCB provider terms; XKDR mirror compilation CC BY 4.0 with CPCB/XKDR attribution."

    def download(self, start=None, end=None, **options):
        # The DOI metadata supplies the actual current transfer location. It requires
        # Globus sign-in, so record that fact and use a documented public CPCB mirror.
        path, _ = self.download_asset(
            "https://api.datacite.org/dois/10.34770/60j3-yp02", "cpcb/princeton/doi-metadata.json"
        )
        metadata = json.loads(path.read_text())
        self.run.params["princeton"] = {
            "doi": metadata["data"]["id"],
            "status": "unavailable: repository distributes large dataset via Globus sign-in",
            "attempted": [
                "https://datacommons.princeton.edu/discovery/catalog/doi-10-34770-60j3-yp02",
                "https://dataspace.princeton.edu/handle/88435/dsp01zw12z843p?mode=full",
            ],
            "alternative": "https://airquality.xkdr.org/ (public demo, PM2.5 history only)",
        }
        # Retain the actual catalogue response/challenge and failed alternative
        # request in the audit. The accessible DOI metadata identifies Globus.
        for index, url in enumerate(self.run.params["princeton"]["attempted"]):
            try:
                self.download_asset(url, f"cpcb/princeton/catalogue-{index}.html")
            except Exception as exc:
                self.run.params["princeton"].setdefault("responses", []).append(str(exc)[:500])
        self.registry()
        for city in City.objects.all():
            first = date.fromisoformat(start or "2015-01-01")
            last = date.fromisoformat(end or "2019-12-31")
            while first <= last:
                next_month = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
                stop = min(last, next_month - timedelta(days=1))
                try:
                    self.download_window(city, first, stop)
                except Exception as exc:
                    self.fail_asset(f"{city.slug}:{first}:{stop}", exc)
                first = next_month

    def download_window(self, city, start, end):
        relative = f"cpcb/xkdr/{city.slug}/{start}_{end}.csv"
        path, asset = self.download_asset(
            "https://airquality.xkdr.org/v1/measurements",
            relative,
            headers=PUBLIC_HEADERS,
            params={
                "city": city.name,
                "source": "cpcb_caaqm",
                "parameter": "PM2.5",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "format": "csv",
            },
            metadata={
                "city": city.name,
                "publisher": "XKDR Forum",
                "timezone": "Asia/Kolkata",
                "scope": "PM2.5 public mirror; not the Princeton release",
            },
        )
        from .air import csv_rows

        # Demo queries are capped at 10,000. Recursively split inclusive dates;
        # a capped response is retained for audit, never loaded as complete data.
        count = sum(1 for _ in csv_rows(path))
        if count >= 10000:
            asset.metadata["truncated_parent"] = True
            asset.save(update_fields=["metadata", "updated_at"])
            manifest_path = path.with_name(path.name + ".manifest.json")
            manifest = json.loads(manifest_path.read_text())
            manifest["metadata"]["truncated_parent"] = True
            manifest_path.write_text(json.dumps(manifest, indent=2))
            if start == end:
                raise ValueError(
                    "Single city-day exceeds publisher demo cap; no truncated rows loaded"
                )
            middle = start + (end - start) // 2
            self.download_window(city, start, middle)
            self.download_window(city, middle + timedelta(days=1), end)
        if not self.cache.last_cache_hit:
            time.sleep(settings.INGEST_REQUEST_PAUSE)

    def load(self, **options):
        registry = self.registry()
        paths = sorted(
            p
            for directory in ("cpcb/princeton", "cpcb/ccr", "cpcb/xkdr")
            for p in self.cache.root.glob(f"{directory}/**/*.csv")
        )
        if not paths:
            raise SourceUnavailable("No supported CPCB concentration CSVs available")
        for path in paths:
            try:
                manifest_path = path.with_name(path.name + ".manifest.json")
                metadata = (
                    json.loads(manifest_path.read_text()).get("metadata", {})
                    if manifest_path.exists()
                    else {}
                )
                if metadata.get("truncated_parent"):
                    continue
                self.load_csv(path, registry=registry, metadata=metadata)
            except Exception as exc:
                self.fail_asset(path.relative_to(self.cache.root), exc)
