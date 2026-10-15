"""Evidence-only answering, persisted queries and an always-available extractive provider."""

import time

import requests
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.exceptions import NotFound

from .data_tools import call_tool
from .formatting import data_evidence, extractive_answer
from .models import Query
from .providers import choose_provider
from .retrieval import retrieve, validate_filters
from .routing import route_question
from .verification import REFUSAL, verify_answer


def ask(
    question, filters=None, provider=None, retrieval=None, persist=True, context_tool_calls=None
):
    if not isinstance(question, str) or not 1 <= len(question.strip()) <= 2000:
        raise serializers.ValidationError("Use a nonempty question up to 2000 characters")
    question = question.strip()
    started = time.monotonic()
    filters = validate_filters(filters)
    route, planned = route_question(question)
    if context_tool_calls:
        planned = context_tool_calls
        route = "mixed"
    evidence, tool_results, failures = [], [], []
    for call in planned:
        try:
            result = call_tool(call["tool"], call["parameters"])
            tool_results.append(result)
            evidence.append(data_evidence(result, f"E{len(evidence) + 1}"))
        except (serializers.ValidationError, ObjectDoesNotExist, NotFound) as exc:
            failures.append({**call, "error": str(getattr(exc, "detail", exc))})
    retrieved = []
    retrieval_error = None
    if route in {"literature", "mixed"}:
        try:
            retrieved = (retrieval or retrieve)(question, filters)
        except requests.RequestException as exc:
            retrieval_error = type(exc).__name__
            retrieved = retrieve(question, filters, mode="keyword")
        for passage in retrieved:
            # Prespecified conservative relevance screen, before evaluation.
            score = passage.get("rerank_score")
            if score is not None and score < 0.2:
                continue
            evidence.append(
                {
                    "alias": f"E{len(evidence) + 1}",
                    "citation": passage["citation"],
                    "text": passage["text"],
                    "kind": "document",
                }
            )
    selected = choose_provider(provider)
    generation_error = None
    if selected.name == "extractive":
        draft = extractive_answer(question, evidence) or REFUSAL
    else:
        try:
            supplied = [
                {key: value for key, value in item.items() if key in {"alias", "text", "kind"}}
                for item in evidence
            ]
            draft = selected.generate(question, supplied) if evidence else REFUSAL
        except Exception as exc:
            generation_error = type(exc).__name__
            selected = choose_provider("extractive")
            draft = extractive_answer(question, evidence) or REFUSAL
    answer, citations, verification = verify_answer(draft, evidence)
    verification.update(
        tool_errors=failures,
        generation_error=generation_error,
        retrieval_error=retrieval_error,
        retrieved_count=len(retrieved),
        evidence_count=len(evidence),
    )
    elapsed = max(0, int((time.monotonic() - started) * 1000))
    record = None
    if persist:
        record = Query.objects.create(
            question=question,
            filters=filters,
            route=route,
            retrieved_ids=[passage["chunk_id"] for passage in retrieved],
            tool_calls=tool_results,
            answer=answer,
            citations=citations,
            provider=selected.name,
            latency_ms=elapsed,
            verification=verification,
        )
    return {
        "query_id": record.pk if record else None,
        "question": question,
        "answer": answer,
        "citations": citations,
        "route": route,
        "provider": selected.name,
        "latency_ms": elapsed,
        "verification": verification,
        "tool_results": tool_results,
    }
