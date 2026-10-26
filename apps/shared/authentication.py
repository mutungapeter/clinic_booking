from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import ExpiredTokenError, InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings


class PatientJWTAuthentication(JWTAuthentication):
    """Keep JWT verification intact while making failures understandable."""

    def get_validated_token(self, raw_token):
        expired = False
        for token_class in api_settings.AUTH_TOKEN_CLASSES:
            try:
                return token_class(raw_token)
            except ExpiredTokenError:
                expired = True
            except TokenError:
                continue
        if expired:
            raise InvalidToken("Your access token has expired. Refresh it or log in again.")
        raise InvalidToken("Your access token is invalid. Please log in again.")
