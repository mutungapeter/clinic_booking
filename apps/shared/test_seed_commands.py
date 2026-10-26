from datetime import datetime, time
from io import StringIO
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.accounts.models import Patient, User
from apps.appointments.models import Appointment
from apps.appointments.services import cancel_appointment
from apps.doctors.models import Doctor, WorkingHour
from apps.shared.seed_data import DEMO_PATIENT_PASSWORD, DOCTOR_SPECIALIZATIONS, seed_id


class SeedCommandTests(TestCase):
    def setUp(self):
        clock = patch(
            "django.utils.timezone.now",
            return_value=datetime(2030, 1, 7, 8, tzinfo=ZoneInfo("Africa/Nairobi")),
        )
        clock.start()
        self.addCleanup(clock.stop)

    def command(self, name, **options):
        output = StringIO()
        call_command(name, stdout=output, **options)
        return output.getvalue()

    def seed_dependencies(self):
        self.command("seed_patients")
        self.command("seed_doctors")

    def test_patients_have_hashed_passwords_and_profiles(self):
        self.command("seed_patients", password="Another-demo-password-731!")
        self.assertEqual(User.objects.count(), 10)
        self.assertEqual(Patient.objects.count(), 10)
        user = User.objects.get(username="demo_patient_001")
        self.assertTrue(user.check_password("Another-demo-password-731!"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_patient_rerun_preserves_identity_password_and_edits(self):
        self.command("seed_patients")
        user = User.objects.get(username="demo_patient_001")
        patient_id = user.patient_profile.pk
        user.set_password("My-changed-password-731!")
        user.first_name = "Edited"
        user.save()
        self.command("seed_patients", password="Replacement-password-731!")
        user.refresh_from_db()
        self.assertEqual(User.objects.count(), 10)
        self.assertEqual(Patient.objects.count(), 10)
        self.assertEqual(user.patient_profile.pk, patient_id)
        self.assertTrue(user.check_password("My-changed-password-731!"))
        self.assertEqual(user.first_name, "Edited")

    def test_invalid_password_rolls_back_patient_creation(self):
        with self.assertRaises(CommandError):
            self.command("seed_patients", password="123")
        self.assertFalse(User.objects.exists())
        self.assertFalse(Patient.objects.exists())

    def test_seed_password_can_come_from_environment(self):
        with patch.dict("os.environ", {"SEED_PATIENT_PASSWORD": "Environment-demo-password-731!"}):
            output = self.command("seed_patients")
        user = User.objects.get(username="demo_patient_001")
        self.assertTrue(user.check_password("Environment-demo-password-731!"))
        self.assertNotIn("Environment-demo-password-731!", output)

    def test_default_password_is_documented_demo_password(self):
        with patch.dict("os.environ", {"SEED_PATIENT_PASSWORD": DEMO_PATIENT_PASSWORD}):
            self.command("seed_patients")
        self.assertTrue(User.objects.first().check_password(DEMO_PATIENT_PASSWORD))

    def test_existing_username_conflict_does_not_change_real_account(self):
        original = User.objects.create_user(username="demo_patient_003", password="Original-731!")
        with self.assertRaises(CommandError):
            self.command("seed_patients")
        self.assertEqual(User.objects.count(), 1)
        self.assertFalse(Patient.objects.exists())
        original.refresh_from_db()
        self.assertTrue(original.check_password("Original-731!"))

    def test_doctors_have_schedules_and_no_login_accounts(self):
        self.command("seed_doctors")
        self.assertEqual(Doctor.objects.count(), 5)
        self.assertEqual(WorkingHour.objects.count(), 25)
        self.assertFalse(User.objects.exists())
        self.assertFalse(Doctor.objects.filter(user__isnull=False).exists())
        self.assertEqual(
            set(Doctor.objects.values_list("specialization", flat=True)),
            set(DOCTOR_SPECIALIZATIONS),
        )

    def test_doctor_rerun_fills_blank_specialization_without_creating_duplicates(self):
        self.command("seed_doctors")
        doctor = Doctor.objects.get(pk=seed_id("doctor", 1))
        doctor.specialization = ""
        doctor.save()
        self.command("seed_doctors")
        doctor.refresh_from_db()
        self.assertEqual(doctor.specialization, "Cardiologist")
        self.assertEqual(Doctor.objects.count(), 5)

    def test_doctor_rerun_preserves_custom_schedule_and_active_flag(self):
        self.command("seed_doctors")
        doctor = Doctor.objects.first()
        doctor.is_active = False
        doctor.specialization = "Neurologist"
        doctor.save()
        hours = doctor.working_hours.get(weekday=0)
        hours.start_time = time(10)
        hours.save()
        self.command("seed_doctors")
        doctor.refresh_from_db()
        hours.refresh_from_db()
        self.assertEqual(Doctor.objects.count(), 5)
        self.assertEqual(WorkingHour.objects.count(), 25)
        self.assertFalse(doctor.is_active)
        self.assertEqual(doctor.specialization, "Neurologist")
        self.assertEqual(hours.start_time, time(10))

    def test_appointments_require_seeded_dependencies(self):
        with self.assertRaisesMessage(CommandError, "Seed patients and doctors first"):
            self.command("seed_appointments")
        self.assertFalse(Appointment.objects.exists())

    def test_appointment_rerun_preserves_existing_bookings(self):
        self.seed_dependencies()
        self.command("seed_appointments")
        initial_ids = set(Appointment.objects.values_list("pk", flat=True))
        self.assertEqual(len(initial_ids), 10)
        self.assertEqual(len(set(Appointment.objects.values_list("doctor_id", flat=True))), 5)
        self.command("seed_appointments")
        self.assertEqual(set(Appointment.objects.values_list("pk", flat=True)), initial_ids)
        self.command("seed_appointments", count=12)
        self.assertEqual(Appointment.objects.count(), 12)
        self.assertEqual(len(set(Appointment.objects.values_list("patient_id", flat=True))), 10)

    def test_cancelled_seed_booking_can_be_replaced_without_deleting_history(self):
        self.seed_dependencies()
        self.command("seed_appointments")
        appointment = Appointment.objects.first()
        cancel_appointment(appointment=appointment, patient=appointment.patient, reason="Demo cancellation")
        self.command("seed_appointments")
        self.assertEqual(Appointment.objects.filter(status=Appointment.Status.BOOKED).count(), 10)
        self.assertEqual(Appointment.objects.filter(status=Appointment.Status.CANCELLED).count(), 1)

    def test_insufficient_capacity_rolls_back_new_appointments(self):
        self.seed_dependencies()
        with self.assertRaisesMessage(CommandError, "No new appointments were saved"):
            self.command("seed_appointments", count=81, days=1, start_date="2030-01-07")
        self.assertFalse(Appointment.objects.exists())

    def test_invalid_appointment_options_fail_without_writes(self):
        for options in (
            {"count": 0}, {"days": -1}, {"start_date": "bad-date"},
            {"start_date": "2029-12-31"},
        ):
            with self.subTest(options=options), self.assertRaises(CommandError):
                self.command("seed_appointments", **options)
        self.assertFalse(Appointment.objects.exists())

    def test_weekend_window_does_not_create_out_of_hours_bookings(self):
        self.seed_dependencies()
        with self.assertRaises(CommandError):
            self.command("seed_appointments", days=2, start_date="2030-01-12")
        self.assertFalse(Appointment.objects.exists())
