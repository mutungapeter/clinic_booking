from datetime import time

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.doctors.models import Doctor, WorkingHour
from apps.shared.seed_data import DOCTOR_NAMES, DOCTOR_SPECIALIZATIONS, seed_id


class Command(BaseCommand):
    help = "Create five demo doctors and Monday-Friday 09:00-17:00 working hours."
    requires_migrations_checks = True

    @transaction.atomic
    def handle(self, *args, **options):
        doctors_created = hours_created = specializations_updated = 0
        doctors = sorted(
            (seed_id("doctor", index), first_name, last_name, specialization)
            for index, ((first_name, last_name), specialization) in enumerate(
                zip(DOCTOR_NAMES, DOCTOR_SPECIALIZATIONS, strict=True), start=1,
            )
        )
        for doctor_id, first_name, last_name, specialization in doctors:
            doctor, created = Doctor.objects.get_or_create(
                pk=doctor_id,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "specialization": specialization,
                },
            )
            doctors_created += int(created)
            # Use the same lock as booking writes; preserve existing schedules.
            doctor = Doctor.objects.select_for_update().get(pk=doctor.pk)
            if not doctor.specialization.strip():
                doctor.specialization = specialization
                doctor.save(update_fields=["specialization", "updated_at"])
                specializations_updated += 1
            for weekday in range(5):
                if WorkingHour.objects.filter(doctor=doctor, weekday=weekday).exists():
                    continue
                hours = WorkingHour(
                    doctor=doctor, weekday=weekday, start_time=time(9), end_time=time(17),
                )
                hours.full_clean()
                hours.save()
                hours_created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Doctors ready: {len(DOCTOR_NAMES)}. "
            f"Created {doctors_created} doctors and {hours_created} working periods; "
            f"filled {specializations_updated} blank specializations. "
            "Existing nonblank specializations, doctor details, and schedules preserved."
        ))
