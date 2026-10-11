"""Conservative sentence/citation verification; numeric overlap alone never passes."""

import re
from decimal import Decimal, InvalidOperation

REFUSAL = "Insufficient evidence in the available documents and project data."
CITATION = re.compile(r"\[([^\[\]]+)\]")
EVIDENCE_CITATION = re.compile(r"\[(E\d+)\]")
NUMBER = re.compile(r"(?<![A-Za-z0-9])[-−]?\d+(?:,\d{3})*(?:\.\d+)?(?:[eE][-+]?\d+)?")


def numeric_tokens(text):
    result = set()
    for match in NUMBER.finditer(text):
        try:
            result.add(Decimal(match.group().replace(",", "").replace("−", "-")))
        except InvalidOperation:
            continue
    return result


def normalized(text):
    return re.sub(r"\s+", " ", text).strip().casefold().strip('"“”')


def verify_answer(draft, evidence):
    lookup = {item["alias"]: item for item in evidence}
    if draft.strip() == REFUSAL:
        return (
            REFUSAL,
            [],
            {
                "passed": True,
                "refused": True,
                "claims": 0,
                "supported_claims": 0,
                "removed": [],
                "groundedness": None,
            },
        )
    kept, removed, used = [], [], set()
    claims = 0
    for line in draft.splitlines():
        line = line.strip()
        if not line:
            continue
        if line in {
            "| Field | Value | Citation |",
            "| --- | --- | --- |",
            "| Date | PM2.5 | Citation |",
        }:
            kept.append(line)
            continue
        aliases = EVIDENCE_CITATION.findall(line)
        # Scientific ranges such as [0.77–1.19] are source text, not citation
        # identifiers. Keep them for exact-text and numeric verification.
        content = EVIDENCE_CITATION.sub("", line).strip()
        content = re.sub(r"^[-*]\s+", "", content).strip(' "“”')
        if content.startswith("|"):
            content = re.sub(r"\|\s*\|$", "|", content)
        claims += 1
        reason = None
        if not aliases or any(alias not in lookup for alias in aliases):
            reason = "citation_not_in_evidence"
        else:
            sources = [lookup[alias]["text"] for alias in aliases]
            if not all(numeric_tokens(content).issubset(numeric_tokens(s)) for s in sources):
                reason = "unsupported_number"
            elif not all(normalized(content) in normalized(source) for source in sources):
                reason = "sentence_not_supported_verbatim"
        if reason:
            removed.append({"text": line, "reason": reason})
        else:
            kept.append(line)
            used.update(aliases)
    supported = claims - len(removed)
    if not supported:
        return (
            REFUSAL,
            [],
            {
                "passed": True,
                "refused": True,
                "claims": claims,
                "supported_claims": 0,
                "removed": removed,
                "groundedness": 0.0,
            },
        )
    answer = "\n".join(kept)
    citations = []
    for alias in sorted(used, key=lambda value: int(value[1:])):
        source = lookup[alias]
        reference = source["citation"]
        answer = answer.replace(f"[{alias}]", f"[{reference['label']}]")
        citations.append({**reference, "alias": alias})
    return (
        answer,
        citations,
        {
            "passed": True,
            "refused": False,
            "claims": claims,
            "supported_claims": supported,
            "removed": removed,
            "groundedness": supported / claims,
            "method": (
                "exact source sentences/table rows plus numeric support; not semantic entailment"
            ),
        },
    )
