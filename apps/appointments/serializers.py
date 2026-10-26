from rest_framework import serializers

from apps.shared.fields import AwareDateTimeField, DisplayTimeField

from .models import Appointment
from .services import book_appointment, cancel_appointment, reschedule_appointment


class AppointmentSerializer(serializers.ModelSerializer):
    doctor_id = serializers.UUIDField(read_only=True)
    patient_id = serializers.UUIDField(read_only=True)
    ends_at = serializers.DateTimeField(read_only=True)
    display_time = DisplayTimeField()

    class Meta:
        model = Appointment
        fields = [
            "id", "doctor_id", "patient_id", "starts_at", "ends_at", "display_time", "status",
            "cancellation_reason", "cancelled_at", "created_at", "updated_at",
        ]
        read_only_fields = fields


class BookingSerializer(serializers.Serializer):
    doctor_id = serializers.UUIDField()
    starts_at = AwareDateTimeField()

    def create(self, validated_data):
        return book_appointment(patient=self.context["patient"], **validated_data)

    def to_representation(self, instance):
        return AppointmentSerializer(instance).data


class CancellationSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000, allow_blank=False)

    def validate(self, attrs):
        if "reason" not in attrs:
            raise serializers.ValidationError({"reason": "A cancellation reason is required."})
        return attrs

    def update(self, instance, validated_data):
        return cancel_appointment(
            appointment=instance, patient=self.context["patient"], **validated_data,
        )

    def to_representation(self, instance):
        return AppointmentSerializer(instance).data


class RescheduleSerializer(serializers.Serializer):
    starts_at = AwareDateTimeField()

    def validate(self, attrs):
        if "starts_at" not in attrs:
            raise serializers.ValidationError({
                "starts_at": "A new start time is required, for example 2030-01-07T10:30:00+03:00.",
            })
        return attrs

    def update(self, instance, validated_data):
        return reschedule_appointment(
            appointment=instance, patient=self.context["patient"], **validated_data,
        )

    def to_representation(self, instance):
        return AppointmentSerializer(instance).data
