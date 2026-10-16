from django.views.generic import TemplateView

from apps.forecast.models import Forecast
from apps.forecast.serving import served_forecast
from apps.rag.models import Document
from apps.vayusim.models import ScenarioRun
from apps.warehouse.models import City


class HomeView(TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            city_count=City.objects.count(),
            document_count=Document.objects.filter(status="ready").count(),
            forecast_count=Forecast.objects.count(),
            scenario_count=ScenarioRun.objects.count(),
        )
        context["city_forecasts"] = []
        for city in City.objects.filter(slug__in=["delhi", "mumbai", "bengaluru", "hyderabad"]):
            latest = (
                Forecast.objects.filter(city=city, horizon=1)
                .select_related("city")
                .order_by("-issued_for_date", "-id")
                .first()
            )
            if latest:
                served = served_forecast(latest)
                for key in ("point", "aqi_category"):
                    if key in served:
                        setattr(latest, key, served[key])
                context["city_forecasts"].append(
                    {
                        "city": city,
                        "forecast": latest,
                        "category_label": latest.aqi_category.replace("_", " ").title(),
                    }
                )
        return context


class ForecastPage(TemplateView):
    template_name = "dashboard/forecasts.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cities"] = City.objects.filter(forecast__isnull=False).distinct().order_by("name")
        return context


class ResearchPage(TemplateView):
    template_name = "dashboard/research.html"


class LibraryPage(TemplateView):
    template_name = "dashboard/library.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["documents"] = Document.objects.filter(status="ready").order_by("category", "title")
        return context
