from datetime import datetime, time, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Patient, User
from apps.appointments.models import Appointment

from .models import Doctor, WorkingHour


class DoctorTests(TestCase):
    def setUp(self):
        self.doctor = Doctor.objects.create(
            first_name="Amina", last_name="Otieno", specialization="Cardiologist",
        )
        self.client = APIClient()

    def test_doctor_can_exist_without_account_and_optional_link_clears_on_delete(self):
        self.assertIsNone(self.doctor.user_id)
        user = User.objects.create_user(username="doctor")
        self.doctor.user = user
        self.doctor.save()
        user.delete()
        self.doctor.refresh_from_db()
        self.assertIsNone(self.doctor.user_id)

    def test_public_doctor_list_excludes_inactive_and_hides_user_link(self):
        Doctor.objects.create(first_name="Inactive", last_name="Doctor", is_active=False)
        response = self.client.get("/doctors")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsNone(payload["message"])
        self.assertEqual(payload["data"]["count"], 1)
        self.assertEqual(payload["data"]["results"][0]["specialization"], "Cardiologist")
        self.assertNotIn("user", payload["data"]["results"][0])

    def test_working_hours_validate_order_and_alignment(self):
        for start, end in [(time(10), time(9)), (time(9, 15), time(17))]:
            hours = WorkingHour(doctor=self.doctor, weekday=0, start_time=start, end_time=end)
            with self.assertRaises(ValidationError):
                hours.full_clean()

    def test_schedule_changes_cannot_invalidate_bookings(self):
        zone = ZoneInfo("Africa/Nairobi")
        now = datetime(2030, 1, 7, 8, tzinfo=zone)
        hours = WorkingHour.objects.create(
            doctor=self.doctor, weekday=0, start_time=time(9), end_time=time(17),
        )
        user = User.objects.create_user(username="patient")
        patient = Patient.objects.create(user=user)
        Appointment.objects.create(
            doctor=self.doctor, patient=patient, starts_at=now + timedelta(hours=2),
        )
        hours.start_time = time(11)
        with patch("django.utils.timezone.now", return_value=now):
            with self.assertRaises(ValidationError):
                hours.full_clean()
