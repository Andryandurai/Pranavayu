from django.urls import path

from .api import (
    DayView,
    ExportView,
    GridView,
    PresetsView,
    RunDetailView,
    RunView,
    ScenarioView,
    SectionView,
    StationsView,
)

urlpatterns = [
    path("run/", RunView.as_view(), name="vayusim-run"),
    path("runs/<int:run_id>/", RunDetailView.as_view(), name="vayusim-run-detail"),
    path("runs/<int:run_id>/export.png", ExportView.as_view(), name="vayusim-export"),
    path("runs/<int:run_id>/section/", SectionView.as_view(), name="vayusim-section"),
    path("grid/<int:run_id>.bin", GridView.as_view(), {"kind": "bin"}, name="vayusim-grid"),
    path(
        "grid/<int:run_id>.json", GridView.as_view(), {"kind": "json"}, name="vayusim-grid-header"
    ),
    path("grid/<int:run_id>.png", GridView.as_view(), {"kind": "png"}, name="vayusim-overlay"),
    path("scenarios/<slug:slug>/", ScenarioView.as_view(), name="vayusim-scenario"),
    path("day/", DayView.as_view(), name="vayusim-day"),
    path("presets/", PresetsView.as_view(), name="vayusim-presets"),
    path("stations/", StationsView.as_view(), name="vayusim-stations"),
]
