from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Application, Company
from .serializers import (
    ApplicationSerializer,
    ChangeStatusSerializer,
    CompanySerializer,
)


class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer

    def get_queryset(self):
        return Company.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationSerializer

    def get_queryset(self):
        return (
            Application.objects.filter(user=self.request.user)
            .select_related("company")
            .prefetch_related("events")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        application = self.get_object()  # 404 if it isn't the user's
        serializer = ChangeStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        application.change_status(
            new_status=data["status"],
            notes=data["notes"],
            occurred_at=data.get("occurred_at"),
        )
        # Re-fetch so the response includes the newly created event
        return Response(self.get_serializer(self.get_object()).data)