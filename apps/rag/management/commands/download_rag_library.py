from django.core.management.base import BaseCommand

from apps.rag.library import download_library


class Command(BaseCommand):
    help = "Download/reuse verified real library inputs; retain each failure and SHA256."

    def add_arguments(self, parser):
        parser.add_argument("--keys", nargs="+")

    def handle(self, **options):
        manifest = download_library(options["keys"])
        counts = {
            status: sum(r["status"] == status for r in manifest.values())
            for status in ("downloaded", "unavailable")
        }
        self.stdout.write(str(counts))
