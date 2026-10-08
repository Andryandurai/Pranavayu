import ftplib
import hashlib
import json
import logging
import os
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def safe_url(url):
    for name in ("OPENAQ_API_KEY", "FIRMS_MAP_KEY", "CDS_API_KEY"):
        secret = os.environ.get(name)
        if secret:
            url = url.replace(secret, "REDACTED")
    parts = urlsplit(url)
    query = [
        (key, "REDACTED" if key.lower() in {"key", "apikey", "api_key", "token"} else value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def digest_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class HttpClient:
    def __init__(self, sleep=time.sleep):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "EnviroInsights-India/Phase2 (public-data research)"
        self.sleep = sleep

    def get(self, url, *, params=None, headers=None, stream=False):
        attempts = settings.INGEST_HTTP_ATTEMPTS
        for attempt in range(attempts):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    stream=stream,
                    timeout=(10, settings.INGEST_HTTP_TIMEOUT),
                )
            except requests.RequestException:
                if attempt + 1 == attempts:
                    raise
                self.sleep(min(60, 2**attempt))
                continue
            if response.status_code == 429 or response.status_code >= 500:
                retry_after = response.headers.get(
                    "Retry-After", response.headers.get("x-ratelimit-reset", "")
                )
                try:
                    delay = float(retry_after)
                    if delay > 1_000_000_000:
                        delay = max(0, delay - time.time())
                except ValueError:
                    try:
                        delay = max(
                            0,
                            (
                                parsedate_to_datetime(retry_after) - datetime.now(UTC)
                            ).total_seconds(),
                        )
                    except (ValueError, TypeError):
                        delay = min(60, 2**attempt)
                logger.warning(
                    json.dumps(
                        {
                            "event": "http_retry",
                            "url": safe_url(response.url),
                            "status": response.status_code,
                            "attempt": attempt + 1,
                        }
                    )
                )
                response.close()
                if attempt + 1 == attempts:
                    raise requests.HTTPError(
                        f"HTTP {response.status_code}: {safe_url(response.url)}"
                    )
                self.sleep(max(1, delay))
                continue
            response.raise_for_status()
            if response.headers.get("x-ratelimit-remaining") == "0":
                reset = response.headers.get("x-ratelimit-reset", "60")
                try:
                    delay = float(reset)
                    if delay > 1_000_000_000:
                        delay = max(0, delay - time.time())
                except ValueError:
                    try:
                        delay = max(
                            0, (parsedate_to_datetime(reset) - datetime.now(UTC)).total_seconds()
                        )
                    except (ValueError, TypeError):
                        delay = 60
                self.sleep(max(1, delay))
            return response
        raise RuntimeError("HTTP retry loop exhausted")


class RawCache:
    def __init__(self, client=None, root=None):
        self.client = client or HttpClient()
        self.root = Path(root or settings.RAW_DATA_ROOT).resolve()

    def path(self, relative):
        target = (self.root / relative).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError("Raw cache path must remain inside RAW_DATA_ROOT")
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def download(self, url, relative, *, params=None, headers=None, metadata=None, refresh=False):
        self.last_cache_hit = False
        path = self.path(relative)
        manifest_path = path.with_name(path.name + ".manifest.json")
        request_url = requests.Request("GET", url, params=params).prepare().url
        request_hash = hashlib.sha256(request_url.encode()).hexdigest()
        if path.exists() and manifest_path.exists():
            previous = json.loads(manifest_path.read_text(encoding="utf-8"))
            if previous.get("request_sha256") not in {None, request_hash}:
                # New parameters must not overwrite an earlier run's raw input.
                path = self.path(
                    path.relative_to(self.root).with_name(
                        f"{path.stem}-{request_hash[:16]}{path.suffix}"
                    )
                )
                manifest_path = path.with_name(path.name + ".manifest.json")
        if not refresh and path.exists() and manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if (
                manifest.get("request_sha256") == request_hash
                and digest_file(path) == manifest["sha256"]
            ):
                self.last_cache_hit = True
                return path, manifest
        temporary = path.with_name(path.name + ".part")
        try:
            with self.client.get(url, params=params, headers=headers, stream=True) as response:
                with temporary.open("wb") as handle:
                    for block in response.iter_content(1024 * 1024):
                        if block:
                            handle.write(block)
                content_type = response.headers.get("Content-Type", "")
            if not temporary.stat().st_size:
                raise ValueError("Empty source response")
            if path.suffix.lower() in {".csv", ".tif", ".zip", ".shp"}:
                with temporary.open("rb") as handle:
                    prefix = handle.read(256).lower()
                if b"<html" in prefix or b"<!doctype" in prefix:
                    raise ValueError(
                        "Provider returned an HTML login/challenge instead of source data"
                    )
            if path.exists() and digest_file(path) != digest_file(temporary):
                path = self.path(
                    path.relative_to(self.root).with_name(
                        f"{path.stem}-{digest_file(temporary)[:16]}{path.suffix}"
                    )
                )
                manifest_path = path.with_name(path.name + ".manifest.json")
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        manifest = {
            "url": safe_url(request_url),
            "request_sha256": request_hash,
            "path": path.relative_to(self.root).as_posix(),
            "sha256": digest_file(path),
            "size_bytes": path.stat().st_size,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "content_type": content_type,
            "metadata": metadata or {},
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info(
            json.dumps(
                {
                    "event": "raw_cached",
                    "path": manifest["path"],
                    "size_bytes": manifest["size_bytes"],
                    "sha256": manifest["sha256"],
                }
            )
        )
        return path, manifest

    def local(self, path, metadata=None):
        path = Path(path).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Local source files must be inside RAW_DATA_ROOT")
        manifest_path = path.with_name(path.name + ".manifest.json")
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if digest_file(path) != manifest["sha256"]:
                raise ValueError(f"Raw file SHA256 differs from its manifest: {path.name}")
            return path, manifest
        manifest = {
            "url": "",
            "path": path.relative_to(self.root).as_posix(),
            "sha256": digest_file(path),
            "size_bytes": path.stat().st_size,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "metadata": metadata or {},
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return path, manifest

    def download_ftp(self, url, relative, metadata=None):
        """Anonymous provider FTP, with verified prefix and resumable partial input."""
        parts = urlsplit(url)
        if parts.scheme != "ftp" or parts.username or parts.password:
            raise ValueError("FTP cache supports anonymous provider URLs only")
        path = self.path(relative)
        manifest_path = path.with_name(path.name + ".manifest.json")
        if path.exists() and manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
            if digest_file(path) == manifest["sha256"]:
                self.last_cache_hit = True
                return path, manifest
        temporary = path.with_name(path.name + ".part")
        resumed = temporary.stat().st_size if temporary.exists() else 0
        for attempt in range(settings.INGEST_HTTP_ATTEMPTS):
            try:
                with ftplib.FTP(parts.hostname, timeout=settings.INGEST_HTTP_TIMEOUT) as ftp:
                    ftp.login()
                    ftp.voidcmd("TYPE I")
                    size = ftp.size(parts.path)
                    modified = ftp.sendcmd("MDTM " + parts.path)
                    offset = temporary.stat().st_size if temporary.exists() else 0
                    if offset > size:
                        raise ValueError("Cached partial input is larger than provider file")
                    if offset:
                        # Validate actual bytes before accepting a partial HTTP/FTP
                        # input. A source revision must never be joined to old bytes.
                        for start in {0, max(0, offset - 65536)}:
                            length = min(65536, offset - start)
                            with ftp.transfercmd("RETR " + parts.path, rest=start) as probe:
                                sample = bytearray()
                                while len(sample) < length:
                                    block = probe.recv(length - len(sample))
                                    if not block:
                                        raise ValueError("Incomplete FTP resume probe")
                                    sample.extend(block)
                            # Aborted short probes leave a transfer response;
                            # reconnect before issuing another RETR.
                            with temporary.open("rb") as local:
                                local.seek(start)
                                if local.read(length) != sample:
                                    raise ValueError(
                                        "Partial bytes differ from provider; cannot resume"
                                    )
                            ftp.close()
                            ftp.connect(parts.hostname)
                            ftp.login()
                            ftp.voidcmd("TYPE I")
                    self.last_cache_hit = False
                    last_logged = offset
                    with temporary.open("ab") as output:

                        def write(block, expected_bytes=size):
                            nonlocal last_logged
                            output.write(block)
                            if output.tell() - last_logged >= 64 * 1024 * 1024:
                                last_logged = output.tell()
                                logger.info(
                                    json.dumps(
                                        {
                                            "event": "download_progress",
                                            "path": str(relative),
                                            "bytes": last_logged,
                                            "expected_bytes": expected_bytes,
                                        }
                                    )
                                )

                        if offset < size:
                            ftp.retrbinary(
                                "RETR " + parts.path, write, blocksize=65536, rest=offset or None
                            )
                    if (
                        temporary.stat().st_size != size
                        or ftp.sendcmd("MDTM " + parts.path) != modified
                    ):
                        raise ValueError(
                            "FTP size or source modification time changed during transfer"
                        )
                temporary.replace(path)
                manifest = {
                    "url": url,
                    "path": path.relative_to(self.root).as_posix(),
                    "sha256": digest_file(path),
                    "size_bytes": size,
                    "retrieved_at": datetime.now(UTC).isoformat(),
                    "protocol": "anonymous FTP",
                    "server_modified": modified,
                    "resumed_bytes": resumed,
                    "metadata": metadata or {},
                }
                manifest_path.write_text(json.dumps(manifest, indent=2))
                return path, manifest
            except (OSError, ftplib.Error) as exc:
                if attempt + 1 == settings.INGEST_HTTP_ATTEMPTS:
                    raise
                logger.warning(
                    json.dumps(
                        {"event": "ftp_retry", "attempt": attempt + 1, "reason": type(exc).__name__}
                    )
                )
                self.client.sleep(min(60, 2**attempt))
        raise RuntimeError("FTP retry loop exhausted")
