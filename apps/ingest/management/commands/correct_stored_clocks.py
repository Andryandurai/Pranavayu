import json

from django.core.management.base import BaseCommand

from apps.ingest.clocks import correct_stored_clocks


class Command(BaseCommand):
    help = "Correct verified OpenCity labels to stored UTC once; preserve raw values and links."

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(correct_stored_clocks(), indent=2))
