from django.core.management.base import BaseCommand

from apps.analytics.research_pipeline import run_research


class Command(BaseCommand):
    help = "Run frozen Phase 3B nested validation, refits, explanations and comparisons."

    def add_arguments(self, parser):
        parser.add_argument("--diagnostic-run", type=int, required=True)
        parser.add_argument("--stored-run", type=int, required=True)
        parser.add_argument("--cities", nargs="+")
        parser.add_argument("--no-publish", action="store_true")

    def handle(self, *args, **options):
        self.stdout.write(
            str(
                run_research(
                    options["diagnostic_run"],
                    options["stored_run"],
                    options["cities"],
                    not options["no_publish"],
                )
            )
        )
