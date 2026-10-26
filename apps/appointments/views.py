from django.utils.functional import cached_property
from rest_framework.exceptions import NotFound
from rest_framework.generics import CreateAPIView, ListAPIView, UpdateAPIView

from apps.accounts.services import get_patient

from .models import Appointment
from .serializers import (
    AppointmentSerializer,
    BookingSerializer,
    CancellationSerializer,
    RescheduleSerializer,
)
from .services import upcoming_appointments


class PatientContextMixin:
    @cached_property
    def patient(self):
        return get_patient(self.request.user)

    def get_serializer_context(self):
        if getattr(self, "swagger_fake_view", False):
            return super().get_serializer_context()
        return {**super().get_serializer_context(), "patient": self.patient}


class AppointmentBookingView(PatientContextMixin, CreateAPIView):
    """Book a free half-hour slot for the authenticated patient.

    The start must have a timezone offset, align to a half-hour boundary,
    fall within working hours, and be at least one hour from now.
    """

    swagger_tags = ["Appointments"]
    swagger_response_serializer = AppointmentSerializer
    swagger_error_statuses = (400, 401, 403, 404, 409)
    serializer_class = BookingSerializer
    success_message = "Appointment booked successfully."
    http_method_names = ["post", "options"]


class AppointmentCancellationView(PatientContextMixin, UpdateAPIView):
    """Cancel your future appointment with a nonblank reason.

    The slot is released after commit. An already-cancelled appointment returns 409.
    """

    swagger_tags = ["Appointments"]
    swagger_response_serializer = AppointmentSerializer
    swagger_error_statuses = (400, 401, 403, 404, 409)
    serializer_class = CancellationSerializer
    success_message = "Appointment cancelled successfully."
    http_method_names = ["patch", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Appointment.objects.none()
        return Appointment.objects.filter(patient=self.patient)


class AppointmentRescheduleView(PatientContextMixin, UpdateAPIView):
    """Move your future appointment to another slot for the same doctor.

    Booking rules apply to the new slot. Failed rescheduling preserves the
    original slot. Cancelled appointments cannot be rescheduled.
    """

    swagger_tags = ["Appointments"]
    swagger_response_serializer = AppointmentSerializer
    swagger_error_statuses = (400, 401, 403, 404, 409)
    serializer_class = RescheduleSerializer
    success_message = "Appointment rescheduled successfully."
    http_method_names = ["patch", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Appointment.objects.none()
        return Appointment.objects.filter(patient=self.patient)


class PatientAppointmentListView(PatientContextMixin, ListAPIView):
    """List your upcoming booked appointments, ordered by start time.

    Only the authenticated patient's ID is allowed. Results are paginated.
    """

    swagger_tags = ["Appointments"]
    swagger_error_statuses = (400, 401, 403, 404)
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Appointment.objects.none()
        if self.kwargs["patient_id"] != self.patient.pk:
            raise NotFound("Patient not found.")
        return upcoming_appointments(patient=self.patient)
