from django.core.management.base import BaseCommand

from apps.analytics.research_context import rebuild_stored_tables


class Command(BaseCommand):
    help = "Rebuild all pollutant tables from canonical stored UTC and verify against Run 7 PM2.5."

    def add_arguments(self, parser):
        parser.add_argument("--diagnostic-run", type=int, required=True)

    def handle(self, *args, **options):
        self.stdout.write(str(rebuild_stored_tables(options["diagnostic_run"])))
