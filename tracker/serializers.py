from rest_framework import serializers

from .models import Application, Company, StatusEvent


class StatusEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusEvent
        fields = ["id", "status", "occurred_at", "notes"]
        read_only_fields = fields


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name", "website", "industry", "notes"]

    def validate_name(self, value):
        # DRF doesn't auto-validate our case-insensitive DB constraint,
        # so without this a duplicate would cause a 500 instead of a 400
        qs = Company.objects.filter(
            user=self.context["request"].user, name__iexact=value
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("You already have a company with this name.")
        return value


class UserCompanyField(serializers.PrimaryKeyRelatedField):
    """Only lets users pick from their own companies."""

    def get_queryset(self):
        return Company.objects.filter(user=self.context["request"].user)


class ApplicationSerializer(serializers.ModelSerializer):
    company = UserCompanyField()
    company_name = serializers.CharField(source="company.name", read_only=True)
    events = StatusEventSerializer(many=True, read_only=True)

    class Meta:
        model = Application
        fields = [
            "id", "company", "company_name", "job_title", "source", "job_url",
            "location", "work_mode", "salary_range", "date_applied",
            "description_text", "current_status", "events",
        ]
        read_only_fields = ["current_status"]


class ChangeStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Application.Status.choices)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    occurred_at = serializers.DateTimeField(required=False)