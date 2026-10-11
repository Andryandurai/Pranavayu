from django.shortcuts import get_object_or_404, render
from django.views import View
from rest_framework.exceptions import ValidationError

from .models import DocumentPage
from .service import ask


class AskPage(View):
    def get(self, request):
        return render(request, "rag/ask.html")

    def post(self, request):
        try:
            result = ask(request.POST.get("question", ""))
            context = {"result": result}
        except ValidationError as exc:
            context = {"error": str(exc.detail)}
        template = (
            "rag/answer.html" if request.headers.get("HX-Request") == "true" else "rag/ask.html"
        )
        return render(request, template, context)


class SourcePage(View):
    def get(self, request, document_id, page_number):
        page = get_object_or_404(
            DocumentPage.objects.select_related("document"),
            document_id=document_id,
            page_number=page_number,
        )
        return render(request, "rag/source.html", {"page": page})
