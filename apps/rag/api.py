from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import generics, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .data_tools import ExceedanceParameters, StrictParameters
from .models import Document, DocumentPage
from .retrieval import Filters
from .service import ask


class AskInput(serializers.Serializer):
    question = serializers.CharField(min_length=1, max_length=2000, trim_whitespace=True)
    filters = Filters(required=False)


class AskView(APIView):
    @extend_schema(request=AskInput, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = AskInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(ask(**serializer.validated_data))


class ExplainPayload(StrictParameters):
    city = serializers.CharField(max_length=100, required=False)
    question = serializers.CharField(max_length=2000, required=False)
    year = serializers.IntegerField(min_value=1900, max_value=2100, required=False)
    horizon = serializers.IntegerField(min_value=1, max_value=3, required=False)
    start = serializers.DateField(required=False)
    end = serializers.DateField(required=False)
    kind = serializers.ChoiceField(choices=["raw", "deweathered"], required=False)
    threshold = serializers.FloatField(min_value=0, max_value=1000, required=False)
    scenario_id = serializers.CharField(max_length=100, required=False)
    run_id = serializers.IntegerField(min_value=1, required=False)
    parameters = serializers.DictField(required=False)

    validate_threshold = ExceedanceParameters.validate_threshold

    def validate(self, attrs):
        if bool(attrs.get("start")) != bool(attrs.get("end")):
            raise serializers.ValidationError("Provide both start and end dates")
        if attrs.get("start") and attrs["start"] >= attrs["end"]:
            raise serializers.ValidationError("start must precede end; end is exclusive")
        return attrs


class ExplainInput(serializers.Serializer):
    context_type = serializers.ChoiceField(choices=["chart", "forecast", "scenario"])
    payload = serializers.JSONField()

    def validate_payload(self, value):
        import json

        try:
            encoded = json.dumps(value, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise serializers.ValidationError("Context must be finite JSON") from exc
        if not isinstance(value, dict) or len(encoded) > 10000:
            raise serializers.ValidationError("Use a context object up to 10000 characters")
        allowed = {
            "city",
            "question",
            "year",
            "horizon",
            "start",
            "end",
            "kind",
            "threshold",
            "scenario_id",
            "run_id",
            "parameters",
        }
        if set(value) - allowed:
            raise serializers.ValidationError(
                "Unsupported context fields; client numbers are not database evidence"
            )
        serializer = ExplainPayload(data=value)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class ExplainView(APIView):
    @extend_schema(request=ExplainInput, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = ExplainInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        kind = serializer.validated_data["context_type"]
        payload = serializer.validated_data["payload"]
        city = payload.get("city", "")
        if kind == "scenario":
            question = (
                payload.get("question") or "What are AERMOD model assumptions and limitations?"
            )
        elif kind == "forecast":
            question = (
                payload.get("question")
                or f"Explain the latest replay forecast for {city} and its limitations."
            )
        elif payload.get("start") and payload.get("end"):
            question = payload.get("question") or (
                f"Show {payload.get('kind', 'raw')} monthly PM2.5 in {city} "
                f"from {payload['start']} to {payload['end']}."
            )
        else:
            question = (
                payload.get("question")
                or f"Explain the annual mean PM2.5 in {city} in {payload.get('year', '')}."
            )
        tools = None
        if kind == "scenario" and payload.get("run_id"):
            tools = [{"tool": "vayusim_run", "parameters": {"run_id": payload["run_id"]}}]
        result = ask(question, context_tool_calls=tools) if tools else ask(question)
        result["context_type"] = kind
        result["context_limitation"] = (
            "Client context selects evidence; supplied scenario/chart values "
            "are not verified project results."
        )
        return Response(result)


class DocumentSerializer(serializers.ModelSerializer):
    chunk_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "authors",
            "year",
            "category",
            "source_url",
            "licence_note",
            "sha256",
            "size_bytes",
            "retrieved_at",
            "page_count",
            "parsed_at",
            "status",
            "error_message",
            "source_format",
            "chunk_count",
        ]


class DocumentsView(generics.ListAPIView):
    serializer_class = DocumentSerializer

    def get_queryset(self):
        from django.db.models import Count

        return Document.objects.annotate(chunk_count=Count("chunks")).order_by("title", "pk")


class PageView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, document_id, page_number):
        page = get_object_or_404(
            DocumentPage.objects.select_related("document"),
            document_id=document_id,
            page_number=page_number,
        )
        return Response(
            {
                "document_id": document_id,
                "title": page.document.title,
                "page_number": page.page_number,
                "is_logical_page": page.is_logical_page,
                "text": page.text,
                "sections": page.sections,
                "tables": page.tables,
                "is_ocr": page.is_ocr,
                "sha256": page.document.sha256,
                "source_url": page.document.source_url,
            }
        )
