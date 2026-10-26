import logging

from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework_simplejwt.exceptions import ExpiredTokenError, InvalidToken, TokenError

logger = logging.getLogger(__name__)


class Conflict(APIException):
    status_code = 409
    default_detail = "The request conflicts with the current resource state."
    default_code = "conflict"


def api_exception_handler(exc, context):
    # Simple JWT's refresh view retains the typed verification error as its cause.
    if isinstance(exc, InvalidToken) and isinstance(exc.__cause__, TokenError):
        exc.detail = {
            "detail": (
                "Your session has expired. Please log in again."
                if isinstance(exc.__cause__, ExpiredTokenError)
                else "Your refresh token is invalid. Please log in again."
            ),
        }
    response = exception_handler(exc, context)
    if response is not None:
        return response
    logger.error(
        "Unhandled API exception",
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return Response({"detail": "An unexpected error occurred. Please try again."}, status=500)
