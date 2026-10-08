import pytest
from django.contrib import admin
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.core.admin import CappedCountPaginator
from apps.warehouse.models import FireDetection, Reading, WeatherObservation
from tests.factories import ReadingFactory

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def test_composite_key_admin_changelists_are_read_only(admin_client):
    ReadingFactory()
    for model in (Reading, WeatherObservation, FireDetection):
        model_admin = admin.site.get_model_admin(model)
        response = admin_client.get(f"/admin/warehouse/{model._meta.model_name}/")
        assert response.status_code == 200
        assert not model_admin.has_add_permission(response.wsgi_request)
        assert not model_admin.has_change_permission(response.wsgi_request)
        assert not model_admin.has_delete_permission(response.wsgi_request)
        assert (
            admin_client.get(f"/admin/warehouse/{model._meta.model_name}/add/").status_code == 404
        )


def test_paginator_count_uses_bounded_query(settings):
    ReadingFactory()
    settings.ADMIN_COUNT_CAP = 100
    paginator = CappedCountPaginator(Reading.objects.all(), 100)
    with CaptureQueriesContext(connection) as queries:
        assert paginator.count == 1
    assert len(queries) == 1
    assert "LIMIT 101" in queries[0]["sql"]
