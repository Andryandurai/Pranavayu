import json
import time

from django.conf import settings

from apps.ingest.base import SourceUnavailable
from apps.warehouse.models import City

from .air import AirSource


class OpenCitySource(AirSource):
    slug = "opencity"
    name = "OpenCity CPCB station exports"
    url = "https://data.opencity.in/"
    licence = "OpenCity catalogue: Other (Public Domain); attribute CPCB and the supplying board."

    def download(self, **options):
        for city in City.objects.all():
            try:
                path, _ = self.download_asset(
                    "https://data.opencity.in/api/3/action/package_search",
                    f"opencity/catalogues/{city.slug}.json",
                    params={"q": f"{city.name} air quality", "rows": 100},
                )
                catalogue = json.loads(path.read_text())
                resources = []
                for package in catalogue.get("result", {}).get("results", []):
                    # CKAN full-text search also returns other cities' packages;
                    # validate the dataset identity before assigning city metadata.
                    if package["name"] != f"{city.slug}-hourly-air-quality-reports":
                        continue
                    for resource in package["resources"]:
                        if resource.get("format", "").lower() == "csv":
                            resources.append((resource, package))
                self.run.params.setdefault("catalogue_counts", {})[city.slug] = len(resources)
                for resource, package in resources:
                    try:
                        self.download_asset(
                            resource["url"],
                            f"opencity/{city.slug}/{resource['id']}.csv",
                            metadata={
                                "city": city.name,
                                "resource_name": resource["name"],
                                "package": package["name"],
                                "licence": package.get("license_title"),
                            },
                        )
                        if not self.cache.last_cache_hit:
                            time.sleep(settings.INGEST_REQUEST_PAUSE)
                    except Exception as exc:
                        self.fail_asset(resource["id"], exc)
            except Exception as exc:
                self.fail_asset(city.slug, exc)
        self.registry()

    def load(self, **options):
        registry = self.registry()
        paths = sorted(self.cache.root.glob("opencity/*/*.csv"))
        if not paths:
            raise SourceUnavailable("No OpenCity raw CSVs downloaded")
        for path in paths:
            try:
                manifest_path = path.with_name(path.name + ".manifest.json")
                metadata = (
                    json.loads(manifest_path.read_text()).get("metadata", {})
                    if manifest_path.exists()
                    else {}
                )
                from apps.ingest.clocks import CLOCK_VERSION, approved_clock

                manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
                if approved_clock(path, manifest.get("sha256")):
                    metadata["published_clock_timezone"] = "Asia/Kolkata"
                    self.run.params["timestamp_clock_version"] = CLOCK_VERSION
                else:
                    import csv

                    from apps.ingest.models import IngestionRun

                    with path.open(encoding="utf-8-sig", newline="") as stream:
                        fields = next(csv.reader(stream))
                    canonical = (
                        self.run.params.get("timestamp_clock_version") == CLOCK_VERSION
                        or IngestionRun.objects.filter(
                            source__slug="opencity", params__timestamp_clock_version=CLOCK_VERSION
                        ).exists()
                    )
                    if canonical and "Timestamp" in fields:
                        raise SourceUnavailable(
                            "Unverified new publisher clock; approve its evidence first"
                        )
                self.load_csv(path, registry=registry, quarter=True, metadata=metadata)
            except Exception as exc:
                self.fail_asset(path.relative_to(self.cache.root), exc)
