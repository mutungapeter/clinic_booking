"""The response contract shared by all REST endpoints."""


def first_error(detail, field=None):
    """Flatten DRF's nested errors into one useful string."""
    if isinstance(detail, dict):
        if not detail:
            return "The request could not be completed."
        key, value = next(iter(detail.items()))
        label = field if key in ("detail", "non_field_errors") else str(key)
        return first_error(value, label)
    if isinstance(detail, (list, tuple)):
        return first_error(detail[0], field) if detail else "Invalid input."
    message = str(detail)
    return f"{field}: {message}" if field else message


def response_payload(*, status_code, data=None, message=None):
    if status_code >= 400:
        return {
            "status": status_code,
            "message": None,
            "data": None,
            "error": first_error(data),
        }
    return {"status": status_code, "message": message, "data": data}
