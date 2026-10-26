from datetime import date, datetime, time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import Patient
from apps.appointments.models import Appointment
from apps.appointments.services import book_appointment
from apps.doctors.models import Doctor
from apps.doctors.services import available_slots
from apps.shared.exceptions import Conflict
from apps.shared.seed_data import DOCTOR_NAMES, PATIENT_NAMES, patient_username, seed_id


class Command(BaseCommand):
    help = "Ensure a target number of demo bookings in a future date window."
    requires_migrations_checks = True

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=10, help="Target booked appointments; default: 10.")
        parser.add_argument("--days", type=int, default=14, help="Window length in days; default: 14.")
        parser.add_argument("--start-date", help="Local YYYY-MM-DD date; defaults to tomorrow.")

    @transaction.atomic
    def handle(self, *args, **options):
        target = options["count"]
        days = options["days"]
        if target < 1 or days < 1:
            raise CommandError("--count and --days must be positive integers.")
        try:
            start_date = (
                date.fromisoformat(options["start_date"])
                if options["start_date"]
                else timezone.localdate() + timedelta(days=1)
            )
        except ValueError as exc:
            raise CommandError("--start-date must be a valid YYYY-MM-DD date.") from exc
        if start_date < timezone.localdate():
            raise CommandError("--start-date cannot be in the past.")
        try:
            end_date = start_date + timedelta(days=days)
        except OverflowError as exc:
            raise CommandError("The requested date window is too large.") from exc

        patient_ids = [
            seed_id("patient", patient_username(index))
            for index in range(1, len(PATIENT_NAMES) + 1)
        ]
        doctor_ids = [seed_id("doctor", index) for index in range(1, len(DOCTOR_NAMES) + 1)]
        patients = list(
            Patient.objects.filter(pk__in=patient_ids, user__is_active=True)
            .select_related("user").order_by("user__username")
        )
        doctors = list(
            Doctor.objects.select_for_update().filter(pk__in=doctor_ids, is_active=True).order_by("pk")
        )
        if not patients or not doctors:
            raise CommandError(
                "Seed patients and doctors first: run seed_patients, then seed_doctors. "
                "At least one active demo patient and doctor are required."
            )

        zone = timezone.get_default_timezone()
        start = timezone.make_aware(datetime.combine(start_date, time.min), zone)
        end = timezone.make_aware(datetime.combine(end_date, time.min), zone)
        existing = Appointment.objects.filter(
            patient__in=patients,
            doctor__in=doctors,
            status=Appointment.Status.BOOKED,
            starts_at__gte=max(start, timezone.now()),
            starts_at__lt=end,
        ).count()
        created = 0

        for offset in range(days):
            if existing + created >= target:
                break
            day = start_date + timedelta(days=offset)
            candidates = sorted(
                (slot["starts_at"], doctor.pk)
                for doctor in doctors
                for slot in available_slots(doctor=doctor, date=day)
            )
            for starts_at, doctor_id in candidates:
                if existing + created >= target:
                    break
                patient = patients[(existing + created) % len(patients)]
                try:
                    book_appointment(patient=patient, doctor_id=doctor_id, starts_at=starts_at)
                except (Conflict, ValidationError):
                    # A slot can become too close to now while the command runs.
                    continue
                created += 1

        if existing + created < target:
            raise CommandError(
                f"Only {existing + created} eligible demo bookings fit in this window; "
                f"requested {target}. No new appointments were saved. "
                "Increase --days or review the demo doctors' working hours."
            )
        self.stdout.write(self.style.SUCCESS(
            f"Created {created} appointments; {existing} existing demo bookings preserved. "
            f"Target {target} met for {start_date} through {end_date - timedelta(days=1)}."
        ))
