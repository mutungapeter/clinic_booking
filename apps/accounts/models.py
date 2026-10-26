from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.shared.models import BaseModel


class User(AbstractUser, BaseModel):
    """Django authentication with UUID identity and shared timestamps."""


class Patient(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="patient_profile",
    )

    def __str__(self):
        return self.user.get_full_name() or self.user.username
