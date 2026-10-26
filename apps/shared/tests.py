from datetime import datetime, timedelta, timezone as datetime_timezone

from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.test import APIRequestFactory

from .responses import first_error
from .fields import AwareDateTimeField, ISODateField
from .formatting import display_time_range


class BrokenView(GenericAPIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        raise RuntimeError("private server diagnostic")


class InvalidView(GenericAPIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        raise ValidationError({"starts_at": ["First message", "Second message"]})


class ResponseContractTests(SimpleTestCase):
    def test_validation_is_rendered_as_one_string_with_matching_status(self):
        response = InvalidView.as_view()(APIRequestFactory().get("/example"))
        response.render()
        import json

        payload = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(payload, {
            "status": 400, "message": None, "data": None,
            "error": "starts_at: First message",
        })

    def test_unexpected_error_is_logged_without_leaking_details(self):
        with self.assertLogs("apps.shared.exceptions", level="ERROR"):
            response = BrokenView.as_view()(APIRequestFactory().get("/example"))
        response.render()
        self.assertEqual(response.status_code, 500)
        self.assertNotIn(b"private server diagnostic", response.content)

    def test_nested_errors_are_flattened(self):
        self.assertEqual(first_error({"detail": ["Not found."]}), "Not found.")
        self.assertEqual(first_error({"non_field_errors": ["Invalid booking."]}), "Invalid booking.")


class DateInputMessageTests(SimpleTestCase):
    def test_display_time_converts_utc_and_handles_noon_and_midnight(self):
        for utc_hour, expected in (
            (15, "6:00 PM – 6:30 PM EAT"),
            (9, "12:00 PM – 12:30 PM EAT"),
            (21, "12:00 AM – 12:30 AM EAT"),
        ):
            with self.subTest(utc_hour=utc_hour):
                start = datetime(2030, 1, 7, utc_hour, tzinfo=datetime_timezone.utc)
                self.assertEqual(display_time_range(start, start + timedelta(minutes=30)), expected)

    def test_date_accepts_hyphens_and_explains_slash_errors(self):
        field = ISODateField()
        self.assertEqual(field.run_validation("2030-01-07").isoformat(), "2030-01-07")
        with self.assertRaises(ValidationError) as error:
            field.run_validation("2030/01/07")
        self.assertIn("YYYY-MM-DD", str(error.exception.detail))
        self.assertIn("2030-01-07", str(error.exception.detail))

    def test_invalid_and_naive_timestamps_include_format_example(self):
        field = AwareDateTimeField()
        for value in ("invalid", "2030-01-07T10:30:00"):
            with self.subTest(value=value), self.assertRaises(ValidationError) as error:
                field.run_validation(value)
            self.assertIn("2030-01-07T10:30:00+03:00", str(error.exception.detail))
