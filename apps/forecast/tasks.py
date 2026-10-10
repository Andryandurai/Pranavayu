from celery import shared_task
from django_celery_beat.models import CrontabSchedule, PeriodicTask


@shared_task(soft_time_limit=870, time_limit=900)
def refresh_forecast_pm():
    from .operations import refresh_live_pm

    run = refresh_live_pm()
    return {"run": run.pk, "status": run.status, "inserted": run.rows_inserted}


@shared_task(soft_time_limit=870, time_limit=900)
def refresh_forecast_weather():
    from .operations import fetch_live_weather

    run = fetch_live_weather()
    return {"run": run.pk, "status": run.status, "inserted": run.rows_inserted}


@shared_task(soft_time_limit=870, time_limit=900)
def daily_forecasts():
    from .operations import issue_forecasts

    return issue_forecasts()


def configure_schedules():
    for name, task, hour, minute in [
        ("Forecast PM inputs daily", "apps.forecast.tasks.refresh_forecast_pm", 23, 35),
        ("Forecast weather daily", "apps.forecast.tasks.refresh_forecast_weather", 23, 40),
        ("PM2.5 forecasts daily", "apps.forecast.tasks.daily_forecasts", 0, 10),
    ]:
        schedule, _ = CrontabSchedule.objects.get_or_create(
            hour=str(hour),
            minute=str(minute),
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
            timezone="Asia/Kolkata",
        )
        PeriodicTask.objects.get_or_create(
            name=name, defaults={"task": task, "crontab": schedule, "enabled": True}
        )
