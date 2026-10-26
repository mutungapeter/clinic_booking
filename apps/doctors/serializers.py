from rest_framework import serializers

from apps.shared.fields import DisplayTimeField, ISODateField

from .models import Doctor


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ["id", "first_name", "last_name", "specialization"]


class AvailabilityQuerySerializer(serializers.Serializer):
    date = ISODateField()


class SlotSerializer(serializers.Serializer):
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    display_time = DisplayTimeField()


class AvailabilitySerializer(serializers.Serializer):
    doctor_id = serializers.UUIDField()
    date = serializers.DateField()
    slots = SlotSerializer(many=True)
