from rest_framework.routers import DefaultRouter

from .views import ApplicationViewSet, CompanyViewSet

router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="company")
router.register("applications", ApplicationViewSet, basename="application")

urlpatterns = router.urls