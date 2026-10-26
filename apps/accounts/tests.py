from django.test import TestCase
from rest_framework.test import APIClient

from .models import Patient, User


class AccountAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.credentials = {"username": "patient", "password": "A-secure-password-7319!"}

    def test_registration_hashes_password_and_creates_profile(self):
        response = self.client.post("/auth/register", self.credentials, format="json")
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username="patient")
        self.assertTrue(user.check_password(self.credentials["password"]))
        self.assertNotEqual(user.password, self.credentials["password"])
        self.assertEqual(response.json()["data"]["id"], str(user.patient_profile.pk))
        self.assertNotIn("password", response.json()["data"])

    def test_weak_password_and_duplicate_username_rejected(self):
        response = self.client.post(
            "/auth/register", {"username": "patient", "password": "123"}, format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIsInstance(response.json()["error"], str)
        self.assertEqual(User.objects.count(), 0)
        self.client.post("/auth/register", self.credentials, format="json")
        response = self.client.post("/auth/register", self.credentials, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Patient.objects.count(), 1)

    def test_jwt_obtain_refresh_and_authenticated_request(self):
        user = User.objects.create_user(**self.credentials)
        patient = Patient.objects.create(user=user)
        response = self.client.post("/auth/login", self.credentials, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], 200)
        tokens = response.json()["data"]
        refresh = self.client.post(
            "/auth/token/refresh", {"refresh": tokens["refresh"]}, format="json",
        )
        self.assertEqual(refresh.status_code, 200)
        self.assertIn("access", refresh.json()["data"])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        response = self.client.get(f"/patients/{patient.pk}/appointments")
        self.assertEqual(response.status_code, 200)

    def test_invalid_login_and_refresh_are_normalized(self):
        for endpoint, body in [
            ("/auth/login", self.credentials),
            ("/auth/token/refresh", {"refresh": "invalid"}),
        ]:
            response = self.client.post(endpoint, body, format="json")
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["status"], 401)
            self.assertIsInstance(response.json()["error"], str)
            self.assertIsNone(response.json()["data"])
