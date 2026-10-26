from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    PatientLoginSerializer,
    PatientRegistrationSerializer,
    PatientSerializer,
    TokenPairResponseSerializer,
    TokenRefreshResponseSerializer,
)


class PatientRegistrationView(CreateAPIView):
    """Create a patient account and profile together."""

    swagger_tags = ["Accounts"]
    swagger_response_serializer = PatientSerializer
    swagger_error_statuses = (400,)
    serializer_class = PatientRegistrationSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    success_message = "Patient account created successfully."
    http_method_names = ["post", "options"]


class PatientLoginView(TokenObtainPairView):
    """Sign in with a username and password to obtain JWT tokens."""

    swagger_tags = ["Authentication"]
    serializer_class = PatientLoginSerializer
    swagger_response_serializer = TokenPairResponseSerializer
    swagger_success_status = 200
    swagger_error_statuses = (400, 401)
    success_message = "Signed in successfully."


class PatientTokenRefreshView(TokenRefreshView):
    """Exchange a valid refresh token for a new access token."""

    swagger_tags = ["Authentication"]
    swagger_response_serializer = TokenRefreshResponseSerializer
    swagger_success_status = 200
    swagger_error_statuses = (400, 401)
    success_message = "Access token refreshed successfully."
