from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.db import IntegrityError, close_old_connections, connection, connections, transaction
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from apps.accounts.models import Patient, User
from apps.doctors.models import Doctor, WorkingHour
from apps.shared.exceptions import Conflict

from .models import Appointment
from .services import book_appointment, cancel_appointment, reschedule_appointment

ZONE = ZoneInfo("Africa/Nairobi")
NOW = datetime(2030, 1, 7, 8, tzinfo=ZONE)


class BookingFixtureMixin:
    def setUp(self):
        super().setUp()
        clock = patch("django.utils.timezone.now", return_value=NOW)
        clock.start()
        self.addCleanup(clock.stop)
        self.user = User.objects.create_user(username="patient", password="test-password")
        self.patient = Patient.objects.create(user=self.user)
        self.other_user = User.objects.create_user(username="other", password="test-password")
        self.other_patient = Patient.objects.create(user=self.other_user)
        self.doctor = Doctor.objects.create(first_name="Amina", last_name="Otieno")
        self.hours = WorkingHour.objects.create(
            doctor=self.doctor, weekday=NOW.weekday(), start_time=time(9), end_time=time(17),
        )
        self.start = NOW + timedelta(hours=2)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def book(self, starts_at=None, **extra):
        return self.client.post(
            "/appointments",
            {"doctor_id": str(self.doctor.pk), "starts_at": (starts_at or self.start).isoformat(), **extra},
            format="json",
        )

    def appointment(self, **extra):
        return Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, starts_at=self.start, **extra,
        )

    def slots(self):
        response = self.client.get(
            f"/doctors/{self.doctor.pk}/availability", {"date": self.start.date().isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["data"]["slots"]


class BookingAPITests(BookingFixtureMixin, TestCase):
    def test_booking_success_and_exact_response_contract(self):
        response = self.book()
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(set(payload), {"status", "message", "data"})
        self.assertEqual(payload["status"], 201)
        self.assertEqual(payload["message"], "Appointment booked successfully.")
        self.assertEqual(payload["data"]["status"], "BOOKED")
        self.assertEqual(payload["data"]["display_time"], "10:00 AM – 10:30 AM EAT")
        self.assertEqual(payload["data"]["patient_id"], str(self.patient.pk))
        self.assertEqual(Appointment.objects.count(), 1)

    def test_client_cannot_book_for_another_patient(self):
        response = self.book(patient_id=str(self.other_patient.pk))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Appointment.objects.get().patient_id, self.patient.pk)

    def test_duplicate_booking_returns_conflict(self):
        self.appointment()
        response = self.book()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {
            "status": 409, "message": None, "data": None,
            "error": "This slot is already booked. Choose another available slot.",
        })
        self.assertEqual(Appointment.objects.count(), 1)

    def test_database_enforces_unique_booked_slot(self):
        self.appointment()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Appointment.objects.create(
                patient=self.other_patient, doctor=self.doctor, starts_at=self.start,
            )

    def test_invalid_booking_boundaries(self):
        for start in [
            NOW - timedelta(days=7),
            NOW + timedelta(minutes=30),
            self.start.replace(minute=15),
            self.start.replace(second=1),
            self.start.replace(microsecond=1),
            self.start.replace(hour=17),
            self.start + timedelta(days=1),
        ]:
            with self.subTest(start=start):
                response = self.book(start)
                self.assertEqual(response.status_code, 400)
                self.assertIsInstance(response.json()["error"], str)
                self.assertIsNone(response.json()["data"])
        self.assertFalse(Appointment.objects.exists())

    def test_exact_one_hour_and_last_slot_are_allowed(self):
        self.assertEqual(self.book(NOW + timedelta(hours=1)).status_code, 201)
        self.assertEqual(self.book(self.start.replace(hour=16, minute=30)).status_code, 201)

    def test_immediately_before_cutoff_is_rejected(self):
        with patch("django.utils.timezone.now", return_value=NOW + timedelta(microseconds=1)):
            self.assertEqual(self.book(NOW + timedelta(hours=1)).status_code, 400)

    def test_naive_timestamp_is_rejected(self):
        response = self.client.post(
            "/appointments",
            {"doctor_id": str(self.doctor.pk), "starts_at": "2030-01-07T10:00:00"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("timezone", response.json()["error"])

    def test_inactive_doctor_rejected(self):
        self.doctor.is_active = False
        self.doctor.save()
        self.assertEqual(self.book().status_code, 400)

    def test_missing_fields_return_a_string_error(self):
        response = self.client.post("/appointments", {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIsInstance(response.json()["error"], str)

    def test_authentication_and_patient_profile_required(self):
        self.client.force_authenticate(user=None)
        response = self.book()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["status"], 401)
        staff = User.objects.create_user(username="staff", password="test-password", is_staff=True)
        self.client.force_authenticate(staff)
        self.assertEqual(self.book().status_code, 403)

    def test_invalid_jwt_is_a_normalized_error(self):
        self.client.force_authenticate(user=None)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token")
        response = self.book()
        self.assertEqual(response.status_code, 401)
        self.assertIsInstance(response.json()["error"], str)

    def test_availability_excludes_booked_and_returns_null_message(self):
        self.appointment()
        slots = self.slots()
        self.assertEqual(len(slots), 15)
        self.assertEqual(slots[0]["display_time"], "9:00 AM – 9:30 AM EAT")
        self.assertNotIn(self.start.isoformat(), [slot["starts_at"] for slot in slots])
        response = self.client.get(
            f"/doctors/{self.doctor.pk}/availability", {"date": "2030-01-07"},
        )
        self.assertIsNone(response.json()["message"])

    def test_availability_has_no_past_or_nonworking_slots(self):
        for date in ["2029-12-31", "2030-01-08"]:
            response = self.client.get(f"/doctors/{self.doctor.pk}/availability", {"date": date})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["data"]["slots"], [])

    def test_availability_requires_valid_date(self):
        for params in [{}, {"date": "invalid"}]:
            response = self.client.get(f"/doctors/{self.doctor.pk}/availability", params)
            self.assertEqual(response.status_code, 400)
            self.assertIsInstance(response.json()["error"], str)

    def test_cancellation_releases_slot_and_retains_history(self):
        appointment = self.appointment()
        response = self.client.patch(
            f"/appointments/{appointment.pk}/cancel", {"reason": "Plans changed"}, format="json",
        )
        self.assertEqual(response.status_code, 200)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "CANCELLED")
        self.assertEqual(appointment.cancellation_reason, "Plans changed")
        self.assertIsNotNone(appointment.cancelled_at)
        self.assertIn(self.start.isoformat(), [slot["starts_at"] for slot in self.slots()])
        self.assertEqual(self.book().status_code, 201)
        self.assertEqual(Appointment.objects.count(), 2)

    def test_cancel_reason_required_even_for_patch(self):
        appointment = self.appointment()
        for body in [{}, {"reason": ""}, {"reason": "   "}]:
            response = self.client.patch(
                f"/appointments/{appointment.pk}/cancel", body, format="json",
            )
            self.assertEqual(response.status_code, 400)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "BOOKED")

    def test_repeat_cancel_and_reschedule_cancelled_return_conflict(self):
        appointment = self.appointment(status=Appointment.Status.CANCELLED)
        for action, body in [
            ("cancel", {"reason": "Again"}),
            ("reschedule", {"starts_at": (self.start + timedelta(hours=1)).isoformat()}),
        ]:
            response = self.client.patch(
                f"/appointments/{appointment.pk}/{action}", body, format="json",
            )
            self.assertEqual(response.status_code, 409)

    def test_reschedule_is_atomic_and_releases_original(self):
        appointment = self.appointment()
        new_start = self.start + timedelta(hours=1)
        response = self.client.patch(
            f"/appointments/{appointment.pk}/reschedule",
            {"starts_at": new_start.isoformat()}, format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["id"], str(appointment.pk))
        self.assertEqual(response.json()["data"]["display_time"], "11:00 AM – 11:30 AM EAT")
        appointment.refresh_from_db()
        self.assertEqual(appointment.starts_at, new_start)
        self.assertEqual(self.book().status_code, 201)
        self.assertEqual(self.book(new_start).status_code, 409)

    def test_failed_reschedule_preserves_original(self):
        appointment = self.appointment()
        occupied_start = self.start + timedelta(hours=1)
        Appointment.objects.create(
            doctor=self.doctor, patient=self.other_patient, starts_at=occupied_start,
        )
        for body, code in [
            ({}, 400),
            ({"starts_at": self.start.isoformat()}, 400),
            ({"starts_at": occupied_start.isoformat()}, 409),
            ({"starts_at": self.start.replace(hour=18).isoformat()}, 400),
        ]:
            response = self.client.patch(
                f"/appointments/{appointment.pk}/reschedule", body, format="json",
            )
            self.assertEqual(response.status_code, code)
            appointment.refresh_from_db()
            self.assertEqual(appointment.starts_at, self.start)

    def test_other_patient_cannot_change_or_list_appointments(self):
        appointment = self.appointment()
        self.client.force_authenticate(self.other_user)
        for action, body in [
            ("cancel", {"reason": "Not mine"}),
            ("reschedule", {"starts_at": (self.start + timedelta(hours=1)).isoformat()}),
        ]:
            response = self.client.patch(
                f"/appointments/{appointment.pk}/{action}", body, format="json",
            )
            self.assertEqual(response.status_code, 404)
        response = self.client.get(f"/patients/{self.patient.pk}/appointments")
        self.assertEqual(response.status_code, 404)

    def test_started_appointments_cannot_change(self):
        appointment = self.appointment()
        with patch("django.utils.timezone.now", return_value=self.start):
            for action, body in [
                ("cancel", {"reason": "Too late"}),
                ("reschedule", {"starts_at": (self.start + timedelta(hours=1)).isoformat()}),
            ]:
                response = self.client.patch(
                    f"/appointments/{appointment.pk}/{action}", body, format="json",
                )
                self.assertEqual(response.status_code, 400)

    def test_patient_list_sorted_and_filtered(self):
        later = self.appointment()
        earlier = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, starts_at=self.start - timedelta(minutes=30),
        )
        Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            starts_at=self.start + timedelta(minutes=30), status=Appointment.Status.CANCELLED,
        )
        Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, starts_at=NOW - timedelta(days=7),
        )
        response = self.client.get(f"/patients/{self.patient.pk}/appointments")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["count"], 2)
        self.assertEqual([item["id"] for item in data["results"]], [str(earlier.pk), str(later.pk)])
        self.assertEqual(
            [item["display_time"] for item in data["results"]],
            ["9:30 AM – 10:00 AM EAT", "10:00 AM – 10:30 AM EAT"],
        )
        self.assertIsNone(response.json()["message"])

    def test_action_endpoints_reject_put(self):
        appointment = self.appointment()
        response = self.client.put(
            f"/appointments/{appointment.pk}/cancel", {"reason": "No PUT"}, format="json",
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json()["status"], 405)


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row-level locking.")
class ConcurrentBookingTests(BookingFixtureMixin, TransactionTestCase):
    def test_only_one_of_two_concurrent_requests_books_the_slot(self):
        barrier = Barrier(2)

        def attempt(patient):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    book_appointment(patient=patient, doctor_id=self.doctor.pk, starts_at=self.start)
                    return 201
                except Conflict:
                    return 409
            finally:
                connections["default"].close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(attempt, [self.patient, self.other_patient]))
        self.assertEqual(sorted(outcomes), [201, 409])
        self.assertEqual(Appointment.objects.filter(status=Appointment.Status.BOOKED).count(), 1)

    def test_concurrent_cancellation_and_reschedule_remain_consistent(self):
        appointment = self.appointment()
        barrier = Barrier(2)
        new_start = self.start + timedelta(hours=1)

        def attempt(action):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    if action == "cancel":
                        cancel_appointment(
                            appointment=appointment, patient=self.patient, reason="Plans changed",
                        )
                    else:
                        reschedule_appointment(
                            appointment=appointment, patient=self.patient, starts_at=new_start,
                        )
                    return action, 200
                except Conflict:
                    return action, 409
            finally:
                connections["default"].close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = dict(executor.map(attempt, ["cancel", "reschedule"]))
        self.assertEqual(outcomes["cancel"], 200)
        self.assertIn(outcomes["reschedule"], [200, 409])
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.CANCELLED)
        expected_start = new_start if outcomes["reschedule"] == 200 else self.start
        self.assertEqual(appointment.starts_at, expected_start)
        self.assertFalse(Appointment.objects.filter(status=Appointment.Status.BOOKED).exists())
