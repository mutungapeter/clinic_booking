import os

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from apps.accounts.models import Patient, User
from apps.shared.seed_data import (
    DEMO_PATIENT_PASSWORD,
    PATIENT_NAMES,
    patient_username,
    seed_id,
)


class Command(BaseCommand):
    help = "Create ten demo patient accounts without changing existing accounts."
    requires_migrations_checks = True

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=None,
            help="Password for new accounts; defaults to SEED_PATIENT_PASSWORD or the documented demo password.",
        )

    def handle(self, *args, **options):
        password = options["password"]
        if password is None:
            password = os.environ.get("SEED_PATIENT_PASSWORD", DEMO_PATIENT_PASSWORD)
        users_created = profiles_created = 0
        try:
            with transaction.atomic():
                for index, (first_name, last_name) in enumerate(PATIENT_NAMES, start=1):
                    username = patient_username(index)
                    user, created = User.objects.get_or_create(
                        pk=seed_id("user", username),
                        defaults={
                            "username": username,
                            "first_name": first_name,
                            "last_name": last_name,
                            "email": f"{username}@example.test",
                        },
                    )
                    if created:
                        validate_password(password, user=user)
                        user.set_password(password)
                        user.save(update_fields=["password", "updated_at"])
                        users_created += 1
                    _, created = Patient.objects.get_or_create(
                        pk=seed_id("patient", username), defaults={"user": user},
                    )
                    profiles_created += int(created)
        except ValidationError as exc:
            raise CommandError("Invalid seed password: " + " ".join(exc.messages)) from exc
        except IntegrityError as exc:
            raise CommandError(
                "A demo username or patient relationship conflicts with an existing record. "
                "No patient seed changes were saved."
            ) from exc

        self.stdout.write(self.style.SUCCESS(
            f"Patients ready: {len(PATIENT_NAMES)}. "
            f"Created {users_created} users and {profiles_created} profiles; existing accounts preserved."
        ))
