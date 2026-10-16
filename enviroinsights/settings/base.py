from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parents[2]
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "apps.core.apps.CoreConfig",
    "apps.core.apps.EnviroAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.gis",
    "django.contrib.postgres",
    "rest_framework",
    "rest_framework_gis",
    "drf_spectacular",
    "django_celery_beat",
    "django_celery_results",
    "apps.ingest",
    "apps.warehouse",
    "apps.rag",
    "apps.analytics",
    "apps.forecast",
    "apps.vayusim",
    "apps.dashboard",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "enviroinsights.urls"
WSGI_APPLICATION = "enviroinsights.wsgi.application"
ASGI_APPLICATION = "enviroinsights.asgi.application"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

DATABASES = {"default": env.db("DATABASE_URL", engine="django.contrib.gis.db.backends.postgis")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
DATABASES["default"]["OPTIONS"] = {"connect_timeout": 5}
REDIS_URL = env("REDIS_URL", default="redis://redis:6379/0")
HEALTH_CHECK_TIMEOUT = env.float("HEALTH_CHECK_TIMEOUT", default=2.0)
ADMIN_COUNT_CAP = env.int("ADMIN_COUNT_CAP", default=10000)
RAW_DATA_ROOT = BASE_DIR / "data" / "raw"
MLFLOW_TRACKING_URI = env("MLFLOW_TRACKING_URI", default="http://mlflow:5000")
FORECAST_CITIES = ("hyderabad", "mumbai", "bengaluru", "delhi", "pune", "chennai", "kolkata")
INGEST_HTTP_TIMEOUT = env.int("INGEST_HTTP_TIMEOUT", default=120)
INGEST_HTTP_ATTEMPTS = env.int("INGEST_HTTP_ATTEMPTS", default=4)
INGEST_BATCH_SIZE = env.int("INGEST_BATCH_SIZE", default=2000)
INGEST_REQUEST_PAUSE = env.float("INGEST_REQUEST_PAUSE", default=1.0)
OBSERVATION_API_MAX_DAYS = env.int("OBSERVATION_API_MAX_DAYS", default=31)
FIRMS_BBOX = env("FIRMS_BBOX", default="73,27,78,33")
if ADMIN_COUNT_CAP < 100 or HEALTH_CHECK_TIMEOUT <= 0:
    raise ValueError("ADMIN_COUNT_CAP must be >= 100 and HEALTH_CHECK_TIMEOUT must be positive")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
FILE_UPLOAD_PERMISSIONS = 0o640
for library_setting in ("GEOS_LIBRARY_PATH", "GDAL_LIBRARY_PATH"):
    if env(library_setting, default=""):
        globals()[library_setting] = env(library_setting)

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_FILTER_BACKENDS": ["rest_framework.filters.SearchFilter"],
}
SPECTACULAR_SETTINGS = {
    "TITLE": "EnviroInsights-India API",
    "DESCRIPTION": "Reference catalogue, infrastructure health and traceable observations.",
    "VERSION": "2.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "GisFeatureEnum": ("Feature",),
        "GisFeatureCollectionEnum": ("FeatureCollection",),
        "GisPointEnum": ("Point",),
    },
}
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 270
CELERY_RESULT_EXPIRES = 86400
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_TIMEOUT = HEALTH_CHECK_TIMEOUT
CELERY_BROKER_TRANSPORT_OPTIONS = {"socket_connect_timeout": HEALTH_CHECK_TIMEOUT}
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
        "ingestion_console": {"class": "logging.StreamHandler", "stream": "ext://sys.stdout"},
    },
    "loggers": {
        "apps.ingest": {
            "handlers": ["ingestion_console"],
            "level": env("LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
