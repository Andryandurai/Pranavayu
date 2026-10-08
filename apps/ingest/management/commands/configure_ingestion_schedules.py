from django.core.management.base import BaseCommand

from apps.ingest.tasks import configure_schedules


class Command(BaseCommand):
    help = "Create editable ingestion schedules without changing existing curator settings."

    def handle(self, *args, **options):
        configure_schedules()
        self.stdout.write(
            "OpenAQ hourly, FIRMS six hourly and Open-Meteo daily schedules configured."
        )
