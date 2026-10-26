from rest_framework.renderers import JSONRenderer

from .responses import response_payload


class APIJSONRenderer(JSONRenderer):
    """Apply the same envelope to generic views, JWT views, and API errors."""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        context = renderer_context or {}
        response = context.get("response")
        view = context.get("view")
        status_code = response.status_code if response is not None else 200
        message = getattr(view, "success_message", None) if status_code < 400 else None
        payload = response_payload(status_code=status_code, data=data, message=message)
        return super().render(payload, accepted_media_type, renderer_context)
