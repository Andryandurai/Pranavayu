from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.analytics.api import CoverageView, SeriesView, SummaryView
from apps.analytics.research_api import ComparisonsView, NCAPView, RQ2View
from apps.core.views import HealthView
from apps.dashboard.views import ForecastPage, HomeView, LibraryPage, ResearchPage
from apps.forecast.api import EvaluationView, HistoryView, LatestView
from apps.ingest.api import CompletenessView, FireView, ReadingView, WeatherView
from apps.rag.api import AskView, DocumentsView, ExplainView, PageView
from apps.rag.views import AskPage, SourcePage
from apps.vayusim.views import SimulatorPage
from apps.warehouse.views import CityViewSet, PollutantViewSet, StationViewSet

router = DefaultRouter()
router.register("cities", CityViewSet)
router.register("stations", StationViewSet)
router.register("pollutants", PollutantViewSet)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("simulator/", SimulatorPage.as_view(), name="simulator"),
    path("forecasts/", ForecastPage.as_view(), name="forecasts"),
    path("research/", ResearchPage.as_view(), name="research"),
    path("library/", LibraryPage.as_view(), name="library"),
    path("admin/", admin.site.urls),
    path("ask/", AskPage.as_view(), name="rag-ask-page"),
    path(
        "rag/documents/<int:document_id>/page/<int:page_number>/",
        SourcePage.as_view(),
        name="rag-source-page",
    ),
    path("api/rag/ask/", AskView.as_view(), name="rag-ask"),
    path("api/rag/explain/", ExplainView.as_view(), name="rag-explain"),
    path("api/rag/documents/", DocumentsView.as_view(), name="rag-documents"),
    path(
        "api/rag/documents/<int:document_id>/page/<int:page_number>/",
        PageView.as_view(),
        name="rag-page",
    ),
    path("api/health/", HealthView.as_view(), name="health"),
    path("api/vayusim/", include("apps.vayusim.urls")),
    path("api/forecast/<slug:slug>/latest/", LatestView.as_view(), name="forecast-latest"),
    path("api/forecast/<slug:slug>/history/", HistoryView.as_view(), name="forecast-history"),
    path(
        "api/forecast/<slug:slug>/evaluation/", EvaluationView.as_view(), name="forecast-evaluation"
    ),
    path("api/readings/", ReadingView.as_view(), name="readings"),
    path("api/weather/", WeatherView.as_view(), name="weather"),
    path("api/fires/", FireView.as_view(), name="fires"),
    path("api/completeness/", CompletenessView.as_view(), name="completeness"),
    path("api/analytics/coverage/", CoverageView.as_view(), name="analytics-coverage"),
    path("api/analytics/rq2/<slug:slug>/", RQ2View.as_view(), name="analytics-rq2"),
    path("api/analytics/ncap/", NCAPView.as_view(), name="analytics-ncap"),
    path("api/analytics/comparisons/", ComparisonsView.as_view(), name="analytics-comparisons"),
    path(
        "api/analytics/city/<slug:slug>/summary/", SummaryView.as_view(), name="analytics-summary"
    ),
    path("api/analytics/city/<slug:slug>/series/", SeriesView.as_view(), name="analytics-series"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/", include(router.urls)),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
