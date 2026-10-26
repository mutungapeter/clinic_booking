from django.db import IntegrityError, transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Patient, User


def register_patient(*, username, password, **profile):
    try:
        with transaction.atomic():
            user = User.objects.create_user(username=username, password=password, **profile)
            return Patient.objects.create(user=user)
    except IntegrityError as exc:
        constraint = getattr(getattr(exc.__cause__, "diag", None), "constraint_name", None)
        if constraint == "accounts_user_username_key" or str(exc.__cause__) == (
            "UNIQUE constraint failed: accounts_user.username"
        ):
            raise ValidationError({"username": "A user with that username already exists."}) from exc
        raise


def get_patient(user):
    try:
        return user.patient_profile
    except Patient.DoesNotExist:
        raise PermissionDenied("This account does not have a patient profile.")
