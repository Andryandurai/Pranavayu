from django.core.management.base import BaseCommand

from apps.analytics.hourly_validation import supplement_hourly


class Command(BaseCommand):
    help = "Report random-hour/week/transfer diagnostics for frozen hourly counterparts."

    def add_arguments(self, parser):
        parser.add_argument("--run", type=int, required=True)
        parser.add_argument("--watch", action="store_true")

    def handle(self, *args, **options):
        result = supplement_hourly(options["run"], options["watch"])
        self.stdout.write(f"Hourly diagnostic cities: {len(result['cities'])}")
