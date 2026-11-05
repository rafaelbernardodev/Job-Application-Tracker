from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Application, Company
from .serializers import (
    ApplicationSerializer,
    ChangeStatusSerializer,
    CompanySerializer,
)

from rest_framework.views import APIView

from .analytics import ApplicationAnalytics, to_records

from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic import TemplateView


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

    @action(detail=True, methods=["post"], url_path="change-status", serializer_class=ChangeStatusSerializer)
    def change_status(self, request, pk=None):
        application = self.get_object()  # 404 if it isn't the user's
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        application.change_status(
            new_status=data["status"],
            notes=data["notes"],
            occurred_at=data.get("occurred_at"),
        )
        # Re-fetch so the response includes the newly created event
        refreshed = self.get_object()
        return Response(ApplicationSerializer(refreshed, context=self.get_serializer_context()).data
        )

class AnalyticsView(APIView):
    def get(self, request):
        analytics = ApplicationAnalytics.from_user(request.user)
        return Response({
            "funnel": to_records(analytics.funnel()),
            "response_rate_by_source": to_records(analytics.response_rate_by_source()),
            "time_to_stage": to_records(analytics.time_to_stage()),
            "weekly_volume": to_records(analytics.weekly_volume()),
        })

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "tracker/dashboard.html"