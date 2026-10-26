from zoneinfo import ZoneInfo

from django.utils import timezone

KENYA_TIMEZONE = ZoneInfo("Africa/Nairobi")


def display_time_range(starts_at, ends_at):
    """Format an aware time range in Kenyan time without locale dependencies."""
    def clock(value):
        local = timezone.localtime(value, KENYA_TIMEZONE)
        period = "AM" if local.hour < 12 else "PM"
        return f"{local.hour % 12 or 12}:{local.minute:02d} {period}"

    return f"{clock(starts_at)} – {clock(ends_at)} EAT"
