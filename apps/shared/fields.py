from datetime import datetime

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers

from .formatting import display_time_range


class DisplayTimeField(serializers.CharField):
    """Read-only label for both generated slot dictionaries and appointments."""

    def __init__(self, **kwargs):
        kwargs["source"] = "*"
        kwargs["read_only"] = True
        kwargs.setdefault("help_text", "Kenyan local time (Africa/Nairobi), for display only.")
        super().__init__(**kwargs)

    def to_representation(self, value):
        if isinstance(value, dict):
            return display_time_range(value["starts_at"], value["ends_at"])
        return display_time_range(value.starts_at, value.ends_at)

    class Meta:
        swagger_schema_fields = {"example": "6:00 PM – 6:30 PM EAT"}


class ISODateField(serializers.DateField):
    default_error_messages = {
        "invalid": "Use YYYY-MM-DD, for example 2030-01-07. Slashes are not accepted.",
        "required": "Enter a date in YYYY-MM-DD format, for example 2030-01-07.",
    }

    def __init__(self, **kwargs):
        kwargs.setdefault("help_text", "Format: YYYY-MM-DD. Example: 2030-01-07 (use hyphens).")
        super().__init__(**kwargs)

    class Meta:
        swagger_schema_fields = {"example": "2030-01-07"}


class AwareDateTimeField(serializers.DateTimeField):
    """Reject naive input instead of silently assigning the server timezone."""

    default_error_messages = {
        "invalid": "Use ISO 8601 with a timezone, for example 2030-01-07T10:30:00+03:00.",
        "required": "Enter a start time with a timezone, for example 2030-01-07T10:30:00+03:00.",
    }

    def __init__(self, **kwargs):
        kwargs.setdefault(
            "help_text",
            "Format: YYYY-MM-DDTHH:MM:SS+03:00 or UTC with Z. "
            "Example: 2030-01-07T10:30:00+03:00. "
            "Use a half-hour boundary with zero seconds; allow at least one hour of notice.",
        )
        super().__init__(**kwargs)

    class Meta:
        swagger_schema_fields = {"example": "2030-01-07T10:30:00+03:00"}

    def to_internal_value(self, value):
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            try:
                parsed = parse_datetime(value)
            except (ValueError, TypeError):
                parsed = None
        else:
            parsed = None
        if parsed is not None and timezone.is_naive(parsed):
            raise serializers.ValidationError(
                "Include a timezone offset or Z, for example 2030-01-07T10:30:00+03:00.",
            )
        return super().to_internal_value(value)
