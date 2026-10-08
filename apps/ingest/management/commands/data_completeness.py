import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.ingest.completeness import completeness


class Command(BaseCommand):
    help = "Report station-month coverage, incomplete station-days and city-year PM2.5 coverage."

    def add_arguments(self, parser):
        parser.add_argument("--start")
        parser.add_argument("--end")
        parser.add_argument("--output")

    def handle(self, *args, **options):
        report = completeness(options["start"], options["end"])
        output = json.dumps(report, indent=2)
        if options["output"]:
            Path(options["output"]).write_text(output, encoding="utf-8")
            self.stdout.write(
                json.dumps(
                    {
                        "output": options["output"],
                        "station_months": len(report["station_months"]),
                        "station_days_under_75_percent": len(
                            report["station_days_under_75_percent"]
                        ),
                        "city_years": report["city_years"],
                    }
                )
            )
        else:
            self.stdout.write(output)
