import os

# This is a test-only key. Production always requires a supplied secret.
os.environ.setdefault("DJANGO_SECRET_KEY", "tests-only-enviroinsights-key-never-use-in-production")
# Use DATABASE_URL supplied by Compose or .env; do not fall back to a host database.

from .base import *  # noqa: E402

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1", "web"]
DATABASES["default"]["CONN_MAX_AGE"] = 0
DATABASES["default"]["TEST"] = {"NAME": env("TEST_DATABASE_NAME", default="test_enviroinsights")}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
# Deliberately use the real broker/worker, never eager mode for integration tests.
CELERY_TASK_ALWAYS_EAGER = False
