from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"


class EnviroAdminConfig(AdminConfig):
    default_site = "apps.core.admin_site.EnviroAdminSite"
