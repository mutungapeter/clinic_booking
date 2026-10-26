from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Doctor
from .serializers import AvailabilityQuerySerializer, AvailabilitySerializer, DoctorSerializer
from .services import available_slots


class DoctorListView(ListAPIView):
    """List active doctors, with paginated results."""

    swagger_tags = ["Doctors"]
    swagger_error_statuses = (400, 401, 404)
    queryset = Doctor.objects.filter(is_active=True)
    serializer_class = DoctorSerializer
    permission_classes = [AllowAny]


@method_decorator(name="get", decorator=swagger_auto_schema(query_serializer=AvailabilityQuerySerializer))
class DoctorAvailabilityView(RetrieveAPIView):
    """Return free half-hour slots for a doctor on a clinic-local date.

    Requires a YYYY-MM-DD date. Returns an empty slot list for non-working,
    past, or fully booked days. Slots within one hour of now are excluded.
    """

    swagger_tags = ["Doctors"]
    swagger_error_statuses = (400, 401, 404)
    queryset = Doctor.objects.filter(is_active=True)
    serializer_class = AvailabilitySerializer
    permission_classes = [AllowAny]

    def retrieve(self, request, *args, **kwargs):
        doctor = self.get_object()
        query = AvailabilityQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        date = query.validated_data["date"]
        result = {
            "doctor_id": doctor.id,
            "date": date,
            "slots": available_slots(doctor=doctor, date=date),
        }
        return Response(self.get_serializer(result).data)
