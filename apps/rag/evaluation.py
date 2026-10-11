"""Frozen passage/data expectations and measured retrieval/grounding evaluation."""

import hashlib
import json
import re
import time
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .data_tools import call_tool
from .encoders import EMBED_REVISION, CPUModels, cache_path, computation_revision, save_cache
from .formatting import data_evidence, table_rows
from .library import atomic_json
from .models import Document, DocumentChunk
from .providers import configured_providers
from .retrieval import retrieve
from .service import ask
from .verification import CITATION, REFUSAL, normalized, numeric_tokens

MODES = ("vector", "keyword", "hybrid", "hybrid_rerank")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_evaluation(authored, output):
    if output.exists():
        raise ValueError(
            "Evaluation already frozen; do not overwrite its questions or expectations"
        )
    records = []
    specifications = json.loads(authored.read_text())
    if len(specifications["literature"]) < 80 or len(specifications["data"]) < 30:
        raise ValueError("At least 80 authored literature and 30 data questions required")
    if len(specifications["unanswerable"]) < 10:
        raise ValueError("At least 10 unanswerable questions required")
    for index, entry in enumerate(specifications["literature"], 1):
        doc = Document.objects.get(ingestion_metadata__library_key=entry["source"])
        quote = normalized(entry["source_excerpt"])
        if len(quote) < 25:
            raise ValueError("Use a substantive actual excerpt for the gold passage")
        gold = [c for c in doc.chunks.all() if quote in normalized(c.text)]
        if not gold:
            raise ValueError(f"Authored excerpt not in actual parsed chunks: {entry['question']}")
        records.append(
            {
                "id": f"L{index:03d}",
                "type": "literature",
                **entry,
                "gold_document_id": doc.pk,
                "source_sha256": doc.sha256,
                "gold_chunk_ids": [c.pk for c in gold],
                "gold_pages": sorted(
                    {p for c in gold for p in range(c.page_start, c.page_end + 1)}
                ),
                "gold_sections": sorted({c.section_title for c in gold}),
                "is_logical_page": bool(gold[0].metadata.get("is_logical_page")),
            }
        )
    for index, entry in enumerate(specifications["data"], 1):
        expected = call_tool(entry["tool"], entry["parameters"])
        records.append(
            {
                "id": f"D{index:03d}",
                "type": "data",
                **entry,
                "expected": expected,
                "expected_table_rows": table_rows(expected),
                "expected_numeric_cells": numeric_cells(table_rows(expected)),
                "data_available": expected["values"]["status"] == "available",
            }
        )
    records += [
        {"id": f"U{index:03d}", "type": "unanswerable", "question": question}
        for index, question in enumerate(specifications["unanswerable"], 1)
    ]
    if len({r["question"] for r in records}) != len(records):
        raise ValueError("Evaluation questions must be distinct")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(row, ensure_ascii=False, default=str) + "\n" for row in records),
        encoding="utf-8",
    )
    freeze = {
        "built_at": timezone.now().isoformat(),
        "sha256": digest(output),
        "authored_sha256": digest(authored),
        "count": len(records),
        "counts": {
            kind: sum(r["type"] == kind for r in records)
            for kind in ("literature", "data", "unanswerable")
        },
        "gold_policy": "All same-document chunks containing the authored exact source excerpt",
        "number_policy": (
            "Match numeric values by their displayed field to frozen actual data-tool cells. "
            "Report numeric recall, precision and cell exactness separately from answer coverage. "
            "Unavailable-data questions require refusal and have no invented numeric target."
        ),
        "retrieval_policy": "Known-gold hit@k and fraction-of-known-gold recall@k; MRR through 40",
    }
    atomic_json(output.with_suffix(".freeze.json"), freeze)
    return freeze


def load_evaluation(path):
    freeze = json.loads(path.with_suffix(".freeze.json").read_text())
    if digest(path) != freeze["sha256"]:
        raise ValueError("Frozen evaluation checksum changed")
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()], freeze


def numeric_cells(rows):
    cells = []
    for row in rows:
        pieces = re.split(r"(?<!\\)\|", row)
        if len(pieces) < 4:
            continue
        tokens = numeric_tokens(pieces[2])
        if tokens:
            cells.append(
                {
                    "field": normalized(pieces[1]),
                    "numbers": sorted("0" if n == 0 else str(n.normalize()) for n in tokens),
                    "row": row,
                }
            )
    return cells


def score_data_answer(record, result):
    expected = record["expected_numeric_cells"] if record["data_available"] else []
    actual = numeric_cells(CITATION.sub("", result["answer"]).splitlines())
    observed = {}
    for cell in actual:
        observed.setdefault(cell["field"], set()).update(cell["numbers"])
    correct, extra, exact = 0, 0, 0
    for cell in expected:
        gold = set(cell["numbers"])
        found = observed.get(cell["field"], set())
        correct += len(gold & found)
        extra += len(found - gold)
        exact += int(gold == found)
    return {
        "data_available": record["data_available"],
        "expected_numeric_values": sum(len(c["numbers"]) for c in expected),
        "correct_numeric_values": correct,
        "extra_numeric_values": extra,
        "expected_numeric_cells": len(expected),
        "exact_numeric_cells": exact,
        "answered": result["answer"] != REFUSAL,
        "correct_missing_data_refusal": not record["data_available"]
        and result["answer"] == REFUSAL,
    }


def prime_queries(records, models):
    questions = [r["question"] for r in records if r["type"] != "data"]
    pending = [(q, cache_path("query", q, computation_revision(EMBED_REVISION))) for q in questions]
    pending = [(q, path) for q, path in pending if not path.exists()]
    for start in range(0, len(pending), 8):
        batch = pending[start : start + 8]
        vectors = models.embed([q for q, _ in batch])
        for (_, path), vector in zip(batch, vectors, strict=True):
            save_cache(path, vector)
        print(
            json.dumps(
                {
                    "event": "evaluation_query_embeddings",
                    "done": start + len(batch),
                    "total_pending": len(pending),
                }
            ),
            flush=True,
        )


def mean(values):
    return sum(values) / len(values) if values else None


def retrieval_scores(rows):
    metrics = {}
    for mode in MODES:
        selected = [r for r in rows if r["mode"] == mode]
        metrics[mode] = {
            key: mean([r[key] for r in selected])
            for key in (
                "recall_at_5",
                "recall_at_10",
                "hit_at_5",
                "hit_at_10",
                "mrr",
                "seconds",
            )
        }
        metrics[mode]["questions"] = len(selected)
    return metrics


def evaluate(path, folder):
    records, freeze = load_evaluation(path)
    snapshot = list(
        Document.objects.filter(status="ready").values(
            "pk",
            "sha256",
            "page_count",
            "ingestion_metadata",
        )
    )
    if Document.objects.exclude(status="ready").exists():
        raise ValueError("Finish indexing all downloaded documents before the frozen evaluation")
    folder.mkdir(parents=True, exist_ok=True)
    state = {
        "eval_sha256": freeze["sha256"],
        "corpus": snapshot,
        "chunks": list(DocumentChunk.objects.values_list("pk", flat=True).order_by("pk")),
    }
    state_path = folder / "evaluation-state.json"
    if state_path.exists() and json.loads(state_path.read_text()) != state:
        raise ValueError("Evaluation corpus or frozen input changed; do not mix resumed metrics")
    atomic_json(state_path, state)
    for record in records:
        if record["type"] == "literature":
            if not Document.objects.filter(
                pk=record["gold_document_id"], sha256=record["source_sha256"]
            ).exists():
                raise ValueError("Gold document revision no longer matches the frozen evaluation")
            if DocumentChunk.objects.filter(pk__in=record["gold_chunk_ids"]).count() != len(
                record["gold_chunk_ids"]
            ):
                raise ValueError("Gold chunks no longer exist; do not silently remap judgments")
    models = CPUModels()
    prime_queries(records, models)
    retrieval_path = folder / "retrieval.jsonl"
    previous = (
        [json.loads(line) for line in retrieval_path.read_text().splitlines()]
        if retrieval_path.exists()
        else []
    )
    completed = {(r["id"], r["mode"]) for r in previous}
    with retrieval_path.open("a", encoding="utf-8") as stream:
        for record in records:
            if record["type"] != "literature":
                continue
            gold = set(record["gold_chunk_ids"])
            for mode in MODES:
                if (record["id"], mode) in completed:
                    continue
                start = time.monotonic()
                passages = retrieve(record["question"], record.get("filters"), mode, 40, models)
                ids = [p["chunk_id"] for p in passages]
                rank = next((n for n, identifier in enumerate(ids, 1) if identifier in gold), None)
                row = {
                    "id": record["id"],
                    "mode": mode,
                    "ids": ids,
                    "seconds": time.monotonic() - start,
                    "recall_at_5": len(gold & set(ids[:5])) / len(gold),
                    "recall_at_10": len(gold & set(ids[:10])) / len(gold),
                    "hit_at_5": int(bool(gold & set(ids[:5]))),
                    "hit_at_10": int(bool(gold & set(ids[:10]))),
                    "mrr": 1 / rank if rank else 0,
                }
                stream.write(json.dumps(row) + "\n")
                stream.flush()
                previous.append(row)
            print(json.dumps({"event": "retrieval_evaluated", "id": record["id"]}), flush=True)
    answers_path = folder / "answers.jsonl"
    answers = (
        [json.loads(line) for line in answers_path.read_text().splitlines()]
        if answers_path.exists()
        else []
    )
    done = {(r["id"], r["requested_provider"]) for r in answers}
    for provider in configured_providers():
        with answers_path.open("a", encoding="utf-8") as stream:
            for record in records:
                if (record["id"], provider.name) in done:
                    continue
                result = ask(record["question"], record.get("filters"), provider=provider.name)
                row = {
                    "id": record["id"],
                    "type": record["type"],
                    "requested_provider": provider.name,
                    **result,
                }
                row["audit"] = audit_answer(result)
                if record["type"] == "data":
                    row["data_score"] = score_data_answer(record, result)
                    row["expected_rows"] = len(record["expected_table_rows"])
                    row["correct_rows"] = sum(
                        normalized(expected_row) in normalized(result["answer"])
                        for expected_row in record["expected_table_rows"]
                    )
                    row["tool_matches_frozen"] = any(
                        actual == record["expected"] for actual in result["tool_results"]
                    )
                elif record["type"] == "literature":
                    row["gold_source_cited"] = any(
                        c.get("chunk_id") in record["gold_chunk_ids"] for c in result["citations"]
                    )
                stream.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
                stream.flush()
                answers.append(row)
                print(
                    json.dumps(
                        {
                            "event": "answer_evaluated",
                            "id": record["id"],
                            "provider": result["provider"],
                        }
                    ),
                    flush=True,
                )
    result = {
        "completed_at": timezone.now().isoformat(),
        "evaluation_freeze": freeze,
        "corpus": snapshot,
        "retrieval": retrieval_scores(previous),
        "answers": answer_scores(answers),
        "files": {p.name: digest(p) for p in (path, retrieval_path, answers_path)},
        "metric_limitations": (
            "Known-gold retrieval judgments are incomplete. Grounding uses exact-source "
            "verification, not independent semantic/clinical validity. Numeric scoring matches "
            "frozen displayed-field cells. Missing answers to available data score zero recall; "
            "unavailable-data refusals are reported separately. Gold source citation is not a "
            "semantic question-answer accuracy judgment."
        ),
    }
    atomic_json(folder / "metrics.json", result)
    log_mlflow(path, folder, result)
    return result


def answer_scores(rows):
    result = {}
    for provider in sorted({r["requested_provider"] for r in rows}):
        selected = [r for r in rows if r["requested_provider"] == provider]
        data = [r for r in selected if r["type"] == "data"]
        unknown = [r for r in selected if r["type"] == "unanswerable"]
        claims = sum(r["verification"]["claims"] for r in selected)
        supported = sum(r["verification"]["supported_claims"] for r in selected)
        citations = sum(len(r["citations"]) for r in selected)
        audited_citations = sum(r["audit"]["citation_uses"] for r in selected)
        correct_citations = sum(r["audit"]["correct_citation_uses"] for r in selected)
        emitted_sentences = sum(r["audit"]["sentences"] for r in selected)
        supported_sentences = sum(r["audit"]["supported_sentences"] for r in selected)
        removed = sum(len(r["verification"]["removed"]) for r in selected)
        correct = sum(r.get("correct_rows", 0) for r in data)
        expected = sum(r.get("expected_rows", 0) for r in data)
        numeric = [r["data_score"] for r in data]
        available = [r for r in numeric if r["data_available"]]
        missing = [r for r in numeric if not r["data_available"]]
        correct_numbers = sum(r["correct_numeric_values"] for r in numeric)
        expected_numbers = sum(r["expected_numeric_values"] for r in numeric)
        extra_numbers = sum(r["extra_numeric_values"] for r in numeric)
        expected_cells = sum(r["expected_numeric_cells"] for r in numeric)
        exact_cells = sum(r["exact_numeric_cells"] for r in numeric)
        result[provider] = {
            "questions": len(selected),
            "citations": citations,
            "citation_accuracy": correct_citations / audited_citations
            if audited_citations
            else None,
            "audited_citation_uses": audited_citations,
            "correct_citation_uses": correct_citations,
            "groundedness_before_removal": supported / claims if claims else None,
            "groundedness_emitted": supported_sentences / emitted_sentences
            if emitted_sentences
            else None,
            "emitted_sentences": emitted_sentences,
            "supported_emitted_sentences": supported_sentences,
            "claims": claims,
            "supported_claims": supported,
            "removed_claims": removed,
            "number_correctness": correct_numbers / expected_numbers if expected_numbers else None,
            "numeric_precision": correct_numbers / (correct_numbers + extra_numbers)
            if correct_numbers + extra_numbers
            else None,
            "numeric_cell_exactness": exact_cells / expected_cells if expected_cells else None,
            "correct_numeric_values": correct_numbers,
            "expected_numeric_values": expected_numbers,
            "extra_numeric_values": extra_numbers,
            "available_data_questions": len(available),
            "missing_data_questions": len(missing),
            "available_data_answer_rate": mean([int(r["answered"]) for r in available]),
            "missing_data_refusal_rate": mean(
                [int(r["correct_missing_data_refusal"]) for r in missing]
            ),
            "displayed_row_exactness": correct / expected if expected else None,
            "correct_data_rows": correct,
            "expected_data_rows": expected,
            "data_questions_exact": mean([int(r.get("tool_matches_frozen", False)) for r in data]),
            "correct_refusal_rate": mean([int(r["answer"] == REFUSAL) for r in unknown]),
            "literature_answer_rate": mean(
                [int(r["answer"] != REFUSAL) for r in selected if r["type"] == "literature"]
            ),
            "literature_gold_source_citation_rate": mean(
                [int(r["gold_source_cited"]) for r in selected if r["type"] == "literature"]
            ),
            "latency_seconds_mean": mean([r["latency_ms"] / 1000 for r in selected]),
            "generation_fallbacks": sum(r["provider"] != provider for r in selected),
        }
    return result


def audit_answer(result):
    """Audit final emitted citations/claims against independently fetched source rows."""
    sources = {}
    for reference in result["citations"]:
        if reference["kind"] == "document":
            chunk = DocumentChunk.objects.get(pk=reference["chunk_id"])
            valid = (
                chunk.pk in query_ids(result)
                and chunk.document_id == reference["document_id"]
                and chunk.page_start == reference["page_start"]
                and chunk.document.sha256 == reference["sha256"]
            )
            sources.setdefault(reference["label"], []).append(chunk.text if valid else "")
        else:
            tool = next(
                (t for t in result["tool_results"] if t["citation"]["id"] == reference["id"]), None
            )
            sources.setdefault(reference["label"], []).append(
                data_evidence(tool, "E1")["text"] if tool else ""
            )
    audit = {
        "sentences": 0,
        "supported_sentences": 0,
        "citation_uses": 0,
        "correct_citation_uses": 0,
    }
    if result["answer"] == REFUSAL:
        return audit
    marker = re.compile("\\[(" + "|".join(re.escape(label) for label in sources) + ")\\]")
    for line in result["answer"].splitlines():
        labels = marker.findall(line) if sources else []
        if not labels and (
            not line.strip() or line.startswith("| Field |") or line.startswith("| --- |")
        ):
            continue
        content = marker.sub("", line).strip() if sources else line.strip()
        if content.startswith("|"):
            content = re.sub(r"\|\s*\|$", "|", content)
            sentences = [content]
        else:
            sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", content)
        for sentence in sentences:
            supported = []
            for label in labels:
                candidates = sources.get(label, [])
                # Human citations identify a page/section, which can contain
                # several retrieved chunks. Require valid identities for every
                # associated reference and exact support in at least one chunk.
                valid = (
                    bool(candidates)
                    and all(candidates)
                    and any(
                        normalized(sentence) in normalized(source)
                        and numeric_tokens(sentence).issubset(numeric_tokens(source))
                        for source in candidates
                    )
                )
                audit["citation_uses"] += 1
                audit["correct_citation_uses"] += int(valid)
                supported.append(valid)
            audit["sentences"] += 1
            audit["supported_sentences"] += int(bool(supported) and all(supported))
    return audit


def query_ids(result):
    from .models import Query

    if result.get("query_id"):
        return Query.objects.get(pk=result["query_id"]).retrieved_ids
    return []


def log_mlflow(path, folder, result):
    import mlflow

    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    mlflow.set_experiment("rag")
    with mlflow.start_run(run_name="phase5-frozen-evaluation") as run:
        mlflow.log_params(
            {
                "eval_sha256": digest(path),
                "embedding_revision": EMBED_REVISION,
                "corpus_documents": len(result["corpus"]),
                "evaluation_questions": result["evaluation_freeze"]["count"],
            }
        )
        for mode, metrics in result["retrieval"].items():
            mlflow.log_metrics(
                {
                    f"retrieval.{mode}.{key}": value
                    for key, value in metrics.items()
                    if value is not None
                }
            )
        for provider, metrics in result["answers"].items():
            mlflow.log_metrics(
                {
                    f"answer.{provider}.{key}": value
                    for key, value in metrics.items()
                    if isinstance(value, (int, float))
                }
            )
        mlflow.log_artifact(str(path), "evaluation")
        mlflow.log_artifacts(str(folder), "results")
        result["mlflow_run_id"] = run.info.run_id
        atomic_json(folder / "metrics.json", result)
