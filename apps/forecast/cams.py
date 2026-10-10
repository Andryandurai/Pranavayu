import json

from django.conf import settings

from apps.ingest.base import Source, SourceUnavailable
from apps.warehouse.models import City


class CAMSForecastSource(Source):
    slug = "cams-forecast"
    name = "Open-Meteo CAMS Global archived forecast coverage audit"
    url = "https://open-meteo.com/en/docs/air-quality-api"
    licence = "CC BY 4.0; credit Open-Meteo, CAMS and Copernicus."
    access_method = "api"

    def load(self, cities=None, start="2025-06-30", end="2025-12-31", **options):
        coverage = []
        for city in City.objects.filter(slug__in=cities or settings.FORECAST_CITIES).order_by(
            "slug"
        ):
            try:
                path, asset = self.download_asset(
                    "https://air-quality-api.open-meteo.com/v1/air-quality",
                    f"forecast/cams/{city.slug}/{start}_{end}.json",
                    params={
                        "latitude": city.location.y,
                        "longitude": city.location.x,
                        "start_date": start,
                        "end_date": end,
                        "hourly": ",".join(f"pm2_5_previous_day{lead}" for lead in (2, 3, 4)),
                        "domains": "cams_global",
                        "timezone": "UTC",
                    },
                    metadata={
                        "city": city.slug,
                        "domain": "cams_global",
                        "purpose": "Actual evaluation-period issue-vintage availability audit",
                        "lead_days": [2, 3, 4],
                    },
                )
                payload = json.loads(path.read_text())
                for lead in (2, 3, 4):
                    values = payload["hourly"][f"pm2_5_previous_day{lead}"]
                    count = sum(v is not None for v in values)
                    coverage.append(
                        {
                            "city": city.slug,
                            "horizon": lead - 1,
                            "hours": len(values),
                            "non_null_hours": count,
                            "asset": asset.pk,
                            "sha256": asset.sha256,
                        }
                    )
                    self.run.rows_fetched += len(values)
                self.event("cams_coverage", city=city.slug, coverage=coverage[-3:])
            except Exception as exc:
                self.fail_asset(city.slug, exc)
        self.run.params["coverage"] = coverage
        if coverage and not any(r["non_null_hours"] for r in coverage):
            raise SourceUnavailable(
                "CAMS archived lead forecasts are all null in the evaluation period; "
                "valid-time historical PM2.5 is not a forecast benchmark"
            )
