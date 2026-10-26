from django.urls import path

from .views import PatientLoginView, PatientRegistrationView, PatientTokenRefreshView

app_name = "accounts"

urlpatterns = [
    path("auth/register", PatientRegistrationView.as_view(), name="register"),
    path("auth/login", PatientLoginView.as_view(), name="login"),
    path("auth/token/refresh", PatientTokenRefreshView.as_view(), name="token-refresh"),
]
