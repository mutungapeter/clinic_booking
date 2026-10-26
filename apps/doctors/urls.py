from django.urls import path

from .views import DoctorAvailabilityView, DoctorListView

app_name = "doctors"

urlpatterns = [
    path("doctors", DoctorListView.as_view(), name="list"),
    path("doctors/<uuid:pk>/availability", DoctorAvailabilityView.as_view(), name="availability"),
]
