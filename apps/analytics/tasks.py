from celery import shared_task


@shared_task(name="analytics.run_phase3a", soft_time_limit=14400, time_limit=15000)
def run_phase3a_task(**parameters):
    from .pipeline import run_phase3a

    return run_phase3a(**parameters)
