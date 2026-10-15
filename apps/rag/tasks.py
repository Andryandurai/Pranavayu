from celery import shared_task


@shared_task(soft_time_limit=14370, time_limit=14400)
def ingest_document(document_id):
    from .ingestion import ingest

    return ingest(document_id)


@shared_task(name="rag.rerank_passages", queue="rag-rerank", soft_time_limit=890, time_limit=900)
def rerank_passages(question, texts):
    from .reranker_worker import score_passages

    return score_passages(question, texts)
