from django.contrib.admin import AdminSite, ModelAdmin
from django.contrib.admin.sites import AlreadyRegistered
from django.db import models
from django.urls import path


class ReadOnlyCompositeAdmin(ModelAdmin):
    """Only a changelist: Django 5.2 has no composite-key edit/form support."""

    actions = None
    list_display_links = None
    show_full_result_count = False

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        info = f"{self.model._meta.app_label}_{self.model._meta.model_name}"
        return [
            path("", self.admin_site.admin_view(self.changelist_view), name=f"{info}_changelist")
        ]


class EnviroAdminSite(AdminSite):
    site_header = "EnviroInsights-India curation"
    site_title = "EnviroInsights-India"

    def register(self, model_or_iterable, admin_class=None, **options):
        if not isinstance(model_or_iterable, type):
            for model in model_or_iterable:
                self.register(model, admin_class, **options)
            return
        if isinstance(model_or_iterable, type) and isinstance(
            model_or_iterable._meta.pk, models.CompositePrimaryKey
        ):
            if not admin_class or not issubclass(admin_class, ReadOnlyCompositeAdmin) or options:
                raise ValueError("Composite keys require an explicit read-only changelist admin")
            if model_or_iterable in self._registry:
                raise AlreadyRegistered(f"{model_or_iterable.__name__} is already registered")
            # Restrict the stock admin's unsupported registration to listings without
            # forms, actions, object links, edit/delete routes or admin LogEntry writes.
            self._registry[model_or_iterable] = admin_class(model_or_iterable, self)
            return
        return super().register(model_or_iterable, admin_class, **options)
