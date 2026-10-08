import logging

from django.conf import settings
from django.db import connection
from redis import Redis
from redis.backoff import NoBackoff
from redis.retry import Retry

from enviroinsights.celery import app

logger = logging.getLogger(__name__)
EXTENSIONS = ("postgis", "timescaledb", "vector")


def infrastructure_health():
    checks = {
        "database": {"ok": False},
        "extensions": {name: {"ok": False, "version": None} for name in EXTENSIONS},
        "redis": {"ok": False},
        "celery": {"ok": False},
    }
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            checks["database"]["ok"] = cursor.fetchone()[0] == 1
            cursor.execute(
                "SELECT extname, extversion FROM pg_extension WHERE extname = ANY(%s)",
                [list(EXTENSIONS)],
            )
            for name, version in cursor.fetchall():
                checks["extensions"][name] = {"ok": True, "version": version}
    except Exception:
        logger.exception("Database health check failed")
    try:
        with Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=settings.HEALTH_CHECK_TIMEOUT,
            socket_timeout=settings.HEALTH_CHECK_TIMEOUT,
            retry=Retry(NoBackoff(), 0),
        ) as redis:
            checks["redis"]["ok"] = bool(redis.ping())
    except Exception:
        logger.exception("Redis health check failed")
    try:
        with app.connection_for_read() as broker_connection:
            broker_connection.ensure_connection(max_retries=0)
            replies = (
                app.control.inspect(
                    timeout=settings.HEALTH_CHECK_TIMEOUT, connection=broker_connection
                ).ping()
                or {}
            )
        checks["celery"]["ok"] = any(reply.get("ok") == "pong" for reply in replies.values())
    except Exception:
        logger.exception("Celery worker health check failed")
    ok = all(checks[name]["ok"] for name in ("database", "redis", "celery")) and all(
        item["ok"] for item in checks["extensions"].values()
    )
    return {"ok": ok, "checks": checks}
