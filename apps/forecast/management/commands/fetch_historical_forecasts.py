from django.core.management.base import BaseCommand, CommandError

from apps.forecast.cams import CAMSForecastSource
from apps.forecast.weather import ForecastWeatherSource


class Command(BaseCommand):
    help = "Cache and ingest issue-safe Open-Meteo lead forecasts, preserving provenance."

    def add_arguments(self, parser):
        parser.add_argument("--cities", nargs="+")
        parser.add_argument("--start", default="2024-01-01")
        parser.add_argument("--end", default="2026-01-03")

    def handle(self, **options):
        run = ForecastWeatherSource().execute(
            "load", cities=options["cities"], start=options["start"], end=options["end"]
        )
        self.stdout.write(
            f"IngestionRun {run.pk}: {run.status}; "
            f"fetched={run.rows_fetched}; inserted={run.rows_inserted}"
        )
        if run.status != "success":
            raise CommandError(run.error_message)
        cams = CAMSForecastSource().execute("load", cities=options["cities"])
        self.stdout.write(
            f"CAMS coverage IngestionRun {cams.pk}: {cams.status}; {cams.error_message}"
        )
