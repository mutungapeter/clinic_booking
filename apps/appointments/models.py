from django.conf import settings
from django.db import models

from apps.shared.models import BaseModel


class Appointment(BaseModel):
    class Status(models.TextChoices):
        BOOKED = "BOOKED", "Booked"
        CANCELLED = "CANCELLED", "Cancelled"

    patient = models.ForeignKey(
        "accounts.Patient", on_delete=models.PROTECT, related_name="appointments",
    )
    doctor = models.ForeignKey(
        "doctors.Doctor", on_delete=models.PROTECT, related_name="appointments",
    )
    starts_at = models.DateTimeField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.BOOKED)
    cancellation_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["starts_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "starts_at"],
                condition=models.Q(status="BOOKED"),
                name="unique_booked_doctor_slot",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["BOOKED", "CANCELLED"]),
                name="appointment_valid_status",
            ),
        ]
        indexes = [
            models.Index(fields=["patient", "status", "starts_at"], name="patient_upcoming_idx"),
        ]

    @property
    def ends_at(self):
        return self.starts_at + settings.APPOINTMENT_DURATION

    def __str__(self):
        return f"{self.doctor} at {self.starts_at}"
