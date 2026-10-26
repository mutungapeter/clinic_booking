from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("id", "doctor", "patient", "starts_at", "status")
    list_filter = ("status", "doctor")
    search_fields = ("patient__user__username",)
    readonly_fields = (
        "id", "doctor", "patient", "starts_at", "status", "cancellation_reason",
        "cancelled_at", "created_at", "updated_at",
    )
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
