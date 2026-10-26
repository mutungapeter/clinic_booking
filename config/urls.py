from django.contrib import admin
from django.urls import include, path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.permissions import AllowAny

schema_view = get_schema_view(
    openapi.Info(
        title="Clinic Booking API",
        default_version="v1",
        description=(
            "Patient registration, JWT authentication, doctor availability, and "
            "30-minute appointment booking. Times use explicit timezone offsets. "
            "Bookings and reschedules require at least one hour of notice."
        ),
    ),
    public=True,
    permission_classes=[AllowAny],
    authentication_classes=[],
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="redoc"),
    re_path(r"^swagger(?P<format>\.json|\.yaml)$", schema_view.without_ui(cache_timeout=0), name="schema"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.doctors.urls")),
    path("", include("apps.appointments.urls")),
]
