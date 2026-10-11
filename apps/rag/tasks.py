from celery import shared_task


@shared_task(soft_time_limit=14370, time_limit=14400)
def ingest_document(document_id):
    from .ingestion import ingest

    return ingest(document_id)
