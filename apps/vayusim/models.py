import uuid

from django.contrib.gis.db import models


def share_slug():
    return uuid.uuid4().hex


class Scenario(models.Model):
    name = models.CharField(max_length=200)
    city = models.ForeignKey("warehouse.City", on_delete=models.PROTECT)
    centre = models.PointField(srid=4326)
    sources = models.JSONField()
    weather_mode = models.CharField(max_length=6, choices=[("manual", "Manual"), ("real", "Real")])
    date_hour = models.DateTimeField()
    receptor_height = models.FloatField(default=1.5)
    grid_settings = models.JSONField(default=dict)
    inputs = models.JSONField(default=dict)
    share_slug = models.SlugField(max_length=32, unique=True, default=share_slug)
    created = models.DateTimeField(auto_now_add=True)


class ScenarioRun(models.Model):
    scenario = models.ForeignKey(Scenario, on_delete=models.PROTECT, related_name="runs")
    inputs_hash = models.CharField(max_length=64, unique=True)
    stability_class = models.CharField(max_length=1)
    flags = models.JSONField(default=list)
    summary = models.JSONField(default=dict)
    inputs = models.JSONField(default=dict)
    grid_file_path = models.CharField(max_length=500, blank=True)
    engine_version = models.CharField(max_length=60)
    run_time_ms = models.FloatField()
    created = models.DateTimeField(auto_now_add=True)
