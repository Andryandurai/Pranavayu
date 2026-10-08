import json

from django.core.management.base import CommandError

from apps.ingest.sources.firms import FIRMSsource

from ._source import SourceCommand, run_summary


class Command(SourceCommand):
    source_name = "firms"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--archives-only",
            action="store_true",
            help="Load CSVs already under data/raw/firms/ without an API key.",
        )

    def handle(self, *args, **options):
        if options["archives_only"]:
            run = FIRMSsource().execute("load_archives")
            self.stdout.write(json.dumps(run_summary(run)))
            if run.status in {"failed", "partial"}:
                raise CommandError(f"Run {run.pk}: {run.status}; see IngestionRun error_message")
        else:
            super().handle(*args, **options)
