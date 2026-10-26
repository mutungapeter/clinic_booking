from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import WorkingHour


def working_period(doctor, date):
    return WorkingHour.objects.filter(doctor=doctor, weekday=date.weekday()).first()


def validate_slot(*, doctor, starts_at, now=None):
    """Rules shared by new bookings and reschedules."""
    now = now or timezone.now()
    if not doctor.is_active:
        raise ValidationError("This doctor is not accepting bookings.")
    if timezone.is_naive(starts_at):
        raise ValidationError("Include a timezone offset or Z in the timestamp.")
    if starts_at < now + settings.BOOKING_NOTICE:
        raise ValidationError("Appointments must start at least one hour from now.")
    local_start = timezone.localtime(starts_at, timezone.get_default_timezone())
    local_end = local_start + settings.APPOINTMENT_DURATION
    if local_start.minute not in (0, 30) or local_start.second or local_start.microsecond:
        raise ValidationError(
            "Appointments must start at :00 or :30 with zero seconds, "
            "for example 10:00:00 or 10:30:00."
        )
    hours = working_period(doctor, local_start.date())
    if (
        hours is None
        or local_end.date() != local_start.date()
        or local_start.time() < hours.start_time
        or local_end.time() > hours.end_time
    ):
        raise ValidationError("The appointment must fall within the doctor's working hours.")


def available_slots(*, doctor, date, now=None):
    from apps.appointments.models import Appointment

    now = now or timezone.now()
    hours = working_period(doctor, date)
    if hours is None:
        return []
    zone = timezone.get_default_timezone()
    opening = timezone.make_aware(datetime.combine(date, hours.start_time), zone)
    closing = timezone.make_aware(datetime.combine(date, hours.end_time), zone)
    occupied = set(
        Appointment.objects.filter(
            doctor=doctor,
            status=Appointment.Status.BOOKED,
            starts_at__gte=opening,
            starts_at__lt=closing,
        ).values_list("starts_at", flat=True)
    )
    cutoff = now + settings.BOOKING_NOTICE
    slots = []
    start = opening
    while start + settings.APPOINTMENT_DURATION <= closing:
        if start >= cutoff and start not in occupied:
            slots.append({"starts_at": start, "ends_at": start + settings.APPOINTMENT_DURATION})
        start += settings.APPOINTMENT_DURATION
    return slots


def future_working_hour_bookings(hours):
    """Used by schedule validation and admin deletion protection."""
    from apps.appointments.models import Appointment

    bookings = Appointment.objects.filter(
        doctor_id=hours.doctor_id,
        status=Appointment.Status.BOOKED,
        starts_at__gt=timezone.now(),
    )
    zone = timezone.get_default_timezone()
    return [
        booking for booking in bookings
        if timezone.localtime(booking.starts_at, zone).weekday() == hours.weekday
    ]
