"""Immutable public-document downloads with explicit failures and resumable bodies."""

import hashlib
import html
import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.utils import timezone

from .models import Document


def digest_file(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def public_download(url, part, expected_format, attempts):
    """Retry once; resume only a server-acknowledged byte range."""
    sidecar = part.with_suffix(".url")
    if part.exists() and (not sidecar.exists() or sidecar.read_text() != url):
        part.unlink()
    sidecar.write_text(url)
    for number in (1, 2):
        record = {"url": url, "attempt": number, "at": datetime.now(UTC).isoformat()}
        attempts.append(record)
        try:
            offset = part.stat().st_size if part.exists() else 0
            headers = {"User-Agent": "EnviroInsights-India research library (public documents)"}
            if offset:
                headers["Range"] = f"bytes={offset}-"
            with requests.get(url, headers=headers, stream=True, timeout=(30, 90)) as response:
                record["http_status"] = response.status_code
                response.raise_for_status()
                resume = response.status_code == 206 and response.headers.get(
                    "Content-Range", ""
                ).startswith(f"bytes {offset}-")
                if response.status_code == 206 and not resume:
                    raise ValueError("Unverified Content-Range; refusing to append")
                written = 0
                with part.open("ab" if resume else "wb") as stream:
                    for block in response.iter_content(1024 * 256):
                        if block:
                            stream.write(block)
                            written += len(block)
                length = response.headers.get("Content-Length")
                if (
                    length
                    and not response.headers.get("Content-Encoding")
                    and written != int(length)
                ):
                    raise ValueError("Incomplete response body; retained for retry")
                with part.open("rb") as stream:
                    prefix = stream.read(4096)
                if expected_format == "pdf" and not prefix.lstrip().startswith(b"%PDF-"):
                    part.unlink()
                    raise ValueError("Response is not a PDF")
                if expected_format == "html" and (
                    part.stat().st_size < 500
                    or any(
                        phrase in prefix.lower()
                        for phrase in (
                            b"checking your browser",
                            b"request rejected",
                            b"access denied",
                        )
                    )
                ):
                    part.unlink()
                    raise ValueError("Missing article text or access-control response")
                record["resolved_url"] = response.url
                return response.url, timezone.now()
        except (requests.RequestException, ValueError) as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"[:1000]
    raise ValueError(f"Both attempts failed for {url}")


def register_document(spec, path, digest, source_url, retrieved):
    relative = path.relative_to(settings.BASE_DIR).as_posix()
    document, _ = Document.objects.get_or_create(
        sha256=digest,
        defaults={
            "title": spec["title"],
            "year": spec.get("year"),
            "category": spec["category"],
            "source_url": source_url if source_url.startswith("http") else "",
            "source_path": relative,
            "source_format": spec["format"],
            "licence_note": spec["licence_note"],
            "retrieved_at": retrieved,
            "size_bytes": path.stat().st_size,
            "ingestion_metadata": {
                "library_key": spec["key"],
                "requested_url": spec.get("url"),
                "project_path": spec.get("project_path"),
                "doi": spec.get("doi"),
                "declared_city": spec.get("city"),
            },
        },
    )
    return document


def download_library(keys=None):
    folder = settings.BASE_DIR / "data" / "raw" / "rag"
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / "library.manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    specs = json.loads((settings.BASE_DIR / "data" / "library" / "rag_sources.json").read_text())
    for spec in specs:
        key = spec["key"]
        if keys and key not in keys:
            continue
        previous = manifest.get(key, {})
        if previous.get("path") and not spec.get("project_path"):
            existing = settings.BASE_DIR / previous["path"]
            if existing.exists() and digest_file(existing) == previous["sha256"]:
                register_document(
                    {**spec, "format": previous["format"]},
                    existing,
                    previous["sha256"],
                    previous["source_url"],
                    datetime.fromisoformat(previous["retrieved_at"]),
                )
                print(json.dumps({"document": key, "status": "cache_verified"}), flush=True)
                continue
        attempts = list(previous.get("attempts", []))
        entry = {
            "key": key,
            "title": spec["title"],
            "category": spec["category"],
            "requested_url": spec.get("url"),
            "year": spec.get("year"),
            "licence_note": spec["licence_note"],
            "attempts": attempts,
        }
        part = folder / f"{key}.download.part"
        try:
            reused = False
            if spec.get("project_path"):
                shutil.copy2(settings.BASE_DIR / spec["project_path"], part)
                source_url, retrieved = "project:" + spec["project_path"], timezone.now()
            elif spec.get("reuse_path") and (settings.BASE_DIR / spec["reuse_path"]).exists():
                prior = json.loads(
                    (settings.BASE_DIR / "docs" / "RESEARCH_LIBRARY.json").read_text()
                )
                approved = next(r for r in prior if r["path"] == spec["reuse_path"])
                cached = settings.BASE_DIR / spec["reuse_path"]
                if digest_file(cached) != approved["sha256"]:
                    raise ValueError("Earlier public-cache SHA256 differs from approved manifest")
                shutil.copy2(cached, part)
                source_url, retrieved = approved["url"], timezone.now()
                entry["reused_verified_cache"] = spec["reuse_path"]
                reused = True
            else:
                error = None
                for url_index, url in enumerate([spec["url"], *spec.get("alternatives", [])]):
                    earlier = [a for a in attempts if a["url"] == url]
                    if len(earlier) >= 2 and all(a.get("error") for a in earlier):
                        error = ValueError(f"Already attempted twice without success: {url}")
                        continue
                    file_format = (
                        spec.get("alternative_format", spec["format"])
                        if url_index
                        else spec["format"]
                    )
                    try:
                        source_url, retrieved = public_download(url, part, file_format, attempts)
                        if spec.get("find_pdf") and file_format == "html":
                            page = part.read_text(encoding="utf-8", errors="replace")
                            links = re.findall(r'href=["\']([^"\']+)["\']', page, flags=re.I)
                            links = [
                                urljoin(source_url, html.unescape(link))
                                for link in links
                                if ".pdf" in link.lower() and "9789240034228" in link
                            ]
                            if not links:
                                raise ValueError(
                                    "Guideline landing page contains no matching PDF link"
                                )
                            source_url, retrieved = public_download(links[0], part, "pdf", attempts)
                            file_format = "pdf"
                        spec = {**spec, "format": file_format}
                        break
                    except ValueError as exc:
                        error = exc
                else:
                    raise error
            digest = digest_file(part)
            extension = {"markdown": "md", "html": "html", "pdf": "pdf"}[spec["format"]]
            destination = folder / f"{key}-{digest[:16]}.{extension}"
            if destination.exists():
                part.unlink()
            else:
                part.replace(destination)
            document = register_document(spec, destination, digest, source_url, retrieved)
            entry.update(
                status="downloaded",
                document_id=document.pk,
                path=destination.relative_to(settings.BASE_DIR).as_posix(),
                sha256=digest,
                size_bytes=destination.stat().st_size,
                source_url=source_url,
                retrieved_at=retrieved.isoformat(),
                format=spec["format"],
                reused_cache=reused,
            )
        except Exception as exc:
            entry.update(
                status="unavailable",
                error=f"{type(exc).__name__}: {exc}",
                sha256=None,
                size_bytes=None,
                path=None,
            )
        manifest[key] = entry
        atomic_json(manifest_path, manifest)
        print(
            json.dumps(
                {
                    "document": key,
                    "status": entry["status"],
                    "bytes": entry.get("size_bytes"),
                    "error": entry.get("error"),
                }
            ),
            flush=True,
        )
    return manifest
