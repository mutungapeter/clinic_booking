from datetime import timedelta

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.accounts.models import Patient, User


class TokenErrorMessageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="patient", password="Test-password-731!")
        self.patient = Patient.objects.create(user=self.user)
        self.client = APIClient()
        self.url = f"/patients/{self.patient.pk}/appointments"

    def assert_error(self, response, message):
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {
            "status": 401, "message": None, "data": None, "error": message,
        })

    def test_expired_access_token_has_actionable_message(self):
        token = AccessToken.for_user(self.user)
        token.set_exp(lifetime=timedelta(seconds=-1))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assert_error(
            self.client.get(self.url),
            "Your access token has expired. Refresh it or log in again.",
        )

    def test_invalid_access_token_is_not_reported_as_expired(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token")
        self.assert_error(
            self.client.get(self.url), "Your access token is invalid. Please log in again.",
        )

    def test_refresh_token_cannot_be_used_as_access_token(self):
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assert_error(
            self.client.get(self.url), "Your access token is invalid. Please log in again.",
        )

    def test_expired_refresh_token_requires_login(self):
        token = RefreshToken.for_user(self.user)
        token.set_exp(lifetime=timedelta(seconds=-1))
        response = self.client.post("/auth/token/refresh", {"refresh": str(token)}, format="json")
        self.assert_error(response, "Your session has expired. Please log in again.")

    def test_invalid_refresh_token_is_not_reported_as_expired(self):
        response = self.client.post("/auth/token/refresh", {"refresh": "invalid"}, format="json")
        self.assert_error(response, "Your refresh token is invalid. Please log in again.")

    def test_valid_access_token_still_authenticates(self):
        token = AccessToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(self.client.get(self.url).status_code, 200)
