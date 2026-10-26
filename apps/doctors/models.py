from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.shared.models import BaseModel


class Doctor(BaseModel):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    specialization = models.CharField(max_length=100, blank=True, default="")
    is_active = models.BooleanField(default=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="doctor_profile",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["first_name", "last_name", "id"]

    def __str__(self):
        return f"Dr. {self.first_name} {self.last_name}"


class WorkingHour(BaseModel):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="working_hours")
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["weekday", "start_time"]
        constraints = [
            models.UniqueConstraint(fields=["doctor", "weekday"], name="unique_doctor_weekday"),
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="working_hours_end_after_start",
            ),
            models.CheckConstraint(
                condition=models.Q(weekday__gte=0, weekday__lte=6),
                name="working_hours_valid_weekday",
            ),
        ]

    def clean(self):
        super().clean()
        for field in ("start_time", "end_time"):
            value = getattr(self, field)
            if value and (value.minute not in (0, 30) or value.second or value.microsecond):
                raise ValidationError({field: "Use a half-hour boundary, such as 09:00 or 09:30."})
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({"end_time": "Closing time must be after opening time."})
        if self._state.adding or not self.doctor_id or not self.start_time or not self.end_time:
            return
        original = type(self).objects.get(pk=self.pk)
        if original.doctor_id != self.doctor_id:
            raise ValidationError({"doctor": "Create a separate working period for another doctor."})
        from .services import future_working_hour_bookings

        bookings = future_working_hour_bookings(original)
        zone = timezone.get_default_timezone()
        for booking in bookings:
            start = timezone.localtime(booking.starts_at, zone)
            end = start + settings.APPOINTMENT_DURATION
            if (
                self.weekday != original.weekday
                or start.time() < self.start_time
                or end.time() > self.end_time
            ):
                raise ValidationError("These working hours would invalidate an existing future booking.")

    def __str__(self):
        return f"{self.doctor} - {self.get_weekday_display()}"
