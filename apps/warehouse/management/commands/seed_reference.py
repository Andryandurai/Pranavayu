from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.ingest.models import DataSource
from apps.warehouse.models import City, Pollutant, State
from apps.warehouse.reference import CITIES, POLLUTANTS, SOURCES


class Command(BaseCommand):
    help = "Idempotently load documented real pollutants, source metadata and 12 city centres."

    @transaction.atomic
    def handle(self, *args, **options):
        for code, name, unit, who, hours, naaqs in POLLUTANTS:
            Pollutant.objects.update_or_create(
                code=code,
                defaults={
                    "display_name": name,
                    "unit": unit,
                    "who_guideline_value": who,
                    "who_averaging_hours": hours,
                    "naaqs_24h_value": naaqs,
                },
            )
        for name, slug, url, access, licence, description in SOURCES:
            DataSource.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "url": url,
                    "access_method": access,
                    "licence": licence,
                    "description": description,
                },
            )
        for name, state_name, code, longitude, latitude in CITIES:
            state, _ = State.objects.get_or_create(code=code, defaults={"name": state_name})
            # Preserve curated population, geometry, coordinates and NCAP status on reruns.
            City.objects.get_or_create(
                slug=slugify(name),
                defaults={
                    "name": name,
                    "state": state,
                    "location": Point(longitude, latitude, srid=4326),
                    "is_ncap_nonattainment": True,
                },
            )
        self.stdout.write(
            self.style.SUCCESS(
                "Reference seed complete: 7 pollutants, 12 data sources, 12 cities. "
                "No measurements."
            )
        )
