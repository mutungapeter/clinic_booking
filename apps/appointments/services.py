from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.doctors.models import Doctor
from apps.doctors.services import validate_slot
from apps.shared.exceptions import Conflict

from .models import Appointment


def _check_slot(*, doctor, starts_at, exclude_id=None):
    validate_slot(doctor=doctor, starts_at=starts_at)
    occupied = Appointment.objects.filter(
        doctor=doctor, starts_at=starts_at, status=Appointment.Status.BOOKED,
    )
    if exclude_id is not None:
        occupied = occupied.exclude(pk=exclude_id)
    if occupied.exists():
        raise Conflict("This slot is already booked. Choose another available slot.")


def _save_booking(save):
    """Translate only the known uniqueness conflict, after savepoint rollback."""
    try:
        with transaction.atomic():
            return save()
    except IntegrityError as exc:
        cause = exc.__cause__
        constraint = getattr(getattr(cause, "diag", None), "constraint_name", None)
        sqlite_conflict = str(cause) == (
            "UNIQUE constraint failed: appointments_appointment.doctor_id, "
            "appointments_appointment.starts_at"
        )
        if constraint == "unique_booked_doctor_slot" or sqlite_conflict:
            raise Conflict("This slot is already booked. Choose another available slot.") from exc
        raise


@transaction.atomic
def book_appointment(*, patient, doctor_id, starts_at):
    doctor = get_object_or_404(Doctor.objects.select_for_update(), pk=doctor_id)
    _check_slot(doctor=doctor, starts_at=starts_at)
    return _save_booking(
        lambda: Appointment.objects.create(patient=patient, doctor=doctor, starts_at=starts_at)
    )


def _locked_appointment(*, appointment, patient):
    Doctor.objects.select_for_update().get(pk=appointment.doctor_id)
    return get_object_or_404(
        Appointment.objects.select_for_update(),
        pk=appointment.pk,
        patient=patient,
    )


def _check_changeable(appointment, action):
    if appointment.status == Appointment.Status.CANCELLED:
        raise Conflict("This appointment has already been cancelled.")
    if appointment.starts_at <= timezone.now():
        raise ValidationError(f"An appointment that has already started cannot be {action}.")


@transaction.atomic
def cancel_appointment(*, appointment, patient, reason):
    appointment = _locked_appointment(appointment=appointment, patient=patient)
    _check_changeable(appointment, "cancelled")
    reason = reason.strip()
    if not reason:
        raise ValidationError("A cancellation reason is required.")
    appointment.status = Appointment.Status.CANCELLED
    appointment.cancellation_reason = reason
    appointment.cancelled_at = timezone.now()
    appointment.save(update_fields=["status", "cancellation_reason", "cancelled_at", "updated_at"])
    return appointment


@transaction.atomic
def reschedule_appointment(*, appointment, patient, starts_at):
    appointment = _locked_appointment(appointment=appointment, patient=patient)
    _check_changeable(appointment, "rescheduled")
    if starts_at == appointment.starts_at:
        raise ValidationError(
            "Your appointment is already scheduled for this time. "
            "Choose a different available slot to reschedule."
        )
    doctor = Doctor.objects.get(pk=appointment.doctor_id)
    _check_slot(doctor=doctor, starts_at=starts_at, exclude_id=appointment.pk)
    appointment.starts_at = starts_at

    def save():
        appointment.save(update_fields=["starts_at", "updated_at"])
        return appointment

    return _save_booking(save)


def upcoming_appointments(*, patient):
    return Appointment.objects.filter(
        patient=patient,
        status=Appointment.Status.BOOKED,
        starts_at__gt=timezone.now(),
    ).select_related("doctor").order_by("starts_at", "id")
