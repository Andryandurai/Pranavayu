from rest_framework import serializers


class CheckSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    version = serializers.CharField(required=False, allow_null=True)


class HealthChecksSerializer(serializers.Serializer):
    database = CheckSerializer()
    extensions = serializers.DictField(child=CheckSerializer())
    redis = CheckSerializer()
    celery = CheckSerializer()


class HealthSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    checks = HealthChecksSerializer()
