from django.core.management.base import BaseCommand

from apps.analytics.diagnostic_pipeline import prepare_data


class Command(BaseCommand):
    help = "Prepare Phase 3A2 UTC/alignment, geography, station panel and Hyderabad diagnostics."

    def add_arguments(self, parser):
        parser.add_argument("--clock-shift-hours", type=float, default=0)

    def handle(self, *args, **options):
        run = prepare_data(options["clock_shift_hours"])
        self.stdout.write(f"Phase 3A2 diagnostic data run: {run}")
