from django.urls import path

from .views import (
    AppointmentBookingView,
    AppointmentCancellationView,
    AppointmentRescheduleView,
    PatientAppointmentListView,
)

app_name = "appointments"

urlpatterns = [
    path("appointments", AppointmentBookingView.as_view(), name="book"),
    path("appointments/<uuid:pk>/cancel", AppointmentCancellationView.as_view(), name="cancel"),
    path("appointments/<uuid:pk>/reschedule", AppointmentRescheduleView.as_view(), name="reschedule"),
    path("patients/<uuid:patient_id>/appointments", PatientAppointmentListView.as_view(), name="patient-list"),
]
