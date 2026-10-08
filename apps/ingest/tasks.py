from datetime import UTC, datetime, timedelta

from celery import shared_task
from django_celery_beat.models import IntervalSchedule, PeriodicTask

from .registry import SOURCES


@shared_task(name="ingest.openaq_hourly")
def openaq_hourly():
    return SOURCES["openaq"]().execute("load").pk


@shared_task(name="ingest.firms_six_hourly")
def firms_six_hourly():
    return SOURCES["firms"]().execute("load").pk


@shared_task(name="ingest.weather_daily")
def weather_daily():
    end = datetime.now(UTC).date() - timedelta(days=5)
    return SOURCES["weather"]().execute("load", start=str(end - timedelta(days=2)), end=str(end)).pk


def configure_schedules():
    for name, task, hours in [
        ("Phase 2 OpenAQ hourly", "ingest.openaq_hourly", 1),
        ("Phase 2 FIRMS six hourly", "ingest.firms_six_hourly", 6),
        ("Phase 2 Open-Meteo daily", "ingest.weather_daily", 24),
    ]:
        interval, _ = IntervalSchedule.objects.get_or_create(
            every=hours, period=IntervalSchedule.HOURS
        )
        PeriodicTask.objects.get_or_create(name=name, defaults={"task": task, "interval": interval})
