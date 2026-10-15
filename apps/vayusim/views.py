from django.views.generic import TemplateView

from apps.warehouse.models import City


class SimulatorPage(TemplateView):
    template_name = "vayusim/simulator.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cities"] = [
            {"slug": city.slug, "name": city.name, "location": [city.location.x, city.location.y]}
            for city in City.objects.order_by("name")
        ]
        return context
