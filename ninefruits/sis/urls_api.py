from rest_framework.routers import DefaultRouter

from . import views

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'courses', views.CourseViewSet, basename='course')

# The API URLs are now determined automatically by the router.
urlpatterns = router.urls
