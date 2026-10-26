"""Describe the API envelope without changing domain serializers or views."""

from drf_yasg import openapi
from drf_yasg.inspectors import SwaggerAutoSchema
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny


class EnvelopedAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return getattr(self.view, "swagger_tags", super().get_tags(operation_keys))

    def get_security(self):
        permissions = self.view.get_permissions()
        if not permissions or any(isinstance(permission, AllowAny) for permission in permissions):
            return []
        return [{"Bearer": []}]

    def get_default_responses(self):
        status_code = getattr(
            self.view, "swagger_success_status", 201 if self.method == "POST" else 200,
        )
        serializer_class = getattr(self.view, "swagger_response_serializer", None)
        serializer = serializer_class() if serializer_class else self.get_view_serializer()
        data_schema = self.serializer_to_schema(serializer)
        if isinstance(self.view, ListAPIView):
            data_schema = openapi.Schema(type=openapi.TYPE_ARRAY, items=data_schema)
            if self.should_page():
                data_schema = self.get_paginated_response(data_schema)

        message = getattr(self.view, "success_message", None)
        success = openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["status", "message", "data"],
            properties={
                "status": openapi.Schema(type=openapi.TYPE_INTEGER, enum=[status_code]),
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, x_nullable=message is None,
                    description="Null for successful fetches; a confirmation for successful changes.",
                    **({"example": message} if message else {}),
                ),
                "data": data_schema,
            },
        )
        responses = {str(status_code): openapi.Response("Successful operation", success)}
        for code in getattr(self.view, "swagger_error_statuses", (400, 401, 403, 404)):
            responses[str(code)] = openapi.Response(
                {
                    400: "Invalid request or booking validation failure",
                    401: "Missing or invalid authentication",
                    403: "Account does not have a patient profile",
                    404: "Resource not found or belongs to another patient",
                    409: "Slot occupied or appointment already cancelled",
                }.get(code, "Request failed"),
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    required=["status", "message", "data", "error"],
                    properties={
                        "status": openapi.Schema(type=openapi.TYPE_INTEGER, enum=[code]),
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING, x_nullable=True, description="Always null on failure.",
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT, x_nullable=True, description="Always null on failure.",
                        ),
                        "error": openapi.Schema(
                            type=openapi.TYPE_STRING, description="One meaningful error message.",
                        ),
                    },
                ),
            )
        return responses
