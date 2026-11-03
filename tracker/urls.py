from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import AnalyticsView, ApplicationViewSet, CompanyViewSet

router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="company")
router.register("applications", ApplicationViewSet, basename="application")

urlpatterns = [
    path("analytics/", AnalyticsView.as_view(), name="analytics"),
] + router.urls