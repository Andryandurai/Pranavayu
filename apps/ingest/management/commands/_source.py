import json

from django.core.management.base import BaseCommand, CommandError

from apps.ingest.registry import PUBLIC_SOURCES, SOURCES


def run_summary(run):
    return {
        "run_id": run.pk,
        "source": run.source.slug,
        "status": run.status,
        "rows_fetched": run.rows_fetched,
        "rows_inserted": run.rows_inserted,
        "rows_flagged": run.rows_flagged,
        "message": run.error_message,
    }


class SourceCommand(BaseCommand):
    source_name = ""
    action = "load"

    def add_arguments(self, parser):
        parser.add_argument("--start")
        parser.add_argument("--end")

    def handle(self, *args, **options):
        run = SOURCES[self.source_name]().execute(
            self.action, start=options["start"], end=options["end"]
        )
        self.stdout.write(json.dumps(run_summary(run)))
        if run.status in {"failed", "partial"}:
            raise CommandError(f"Run {run.pk}: {run.status}; see IngestionRun error_message")


class BatchCommand(BaseCommand):
    action = "load"

    def add_arguments(self, parser):
        parser.add_argument("--source", choices=list(SOURCES))
        parser.add_argument("--start")
        parser.add_argument("--end")

    def handle(self, *args, **options):
        names = (
            [options["source"]]
            if options["source"]
            else (PUBLIC_SOURCES if self.action == "download" else SOURCES)
        )
        failed = []
        for name in names:
            if self.action == "download" and name not in PUBLIC_SOURCES:
                raise CommandError("download_sources accepts no-account sources only")
            run = SOURCES[name]().execute(self.action, start=options["start"], end=options["end"])
            self.stdout.write(json.dumps(run_summary(run)))
            if run.status in {"failed", "partial"}:
                failed.append(run.pk)
        if self.action == "load":
            from apps.ingest.tasks import configure_schedules

            configure_schedules()
        if failed:
            raise CommandError(f"Incomplete runs: {failed}; all sources were attempted")
