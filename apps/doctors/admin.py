from django import forms
from django.contrib import admin
from django.db import transaction

from .models import Doctor, WorkingHour
from .services import future_working_hour_bookings


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "specialization", "is_active", "user")
    list_filter = ("is_active", "specialization")
    search_fields = ("first_name", "last_name", "specialization")
    autocomplete_fields = ("user",)
    readonly_fields = ("id", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        with transaction.atomic():
            if change:
                Doctor.objects.select_for_update().get(pk=obj.pk)
            super().save_model(request, obj, form, change)


class WorkingHourForm(forms.ModelForm):
    class Meta:
        model = WorkingHour
        fields = "__all__"

    def clean(self):
        data = super().clean()
        doctor = data.get("doctor")
        # Django admin wraps POST changes in a transaction. Lock before model
        # validation, so a concurrent booking cannot slip past schedule checks.
        if doctor is not None:
            Doctor.objects.select_for_update().get(pk=doctor.pk)
        return data


@admin.register(WorkingHour)
class WorkingHourAdmin(admin.ModelAdmin):
    form = WorkingHourForm
    list_display = ("doctor", "weekday", "start_time", "end_time")
    list_filter = ("weekday",)
    autocomplete_fields = ("doctor",)
    readonly_fields = ("id", "created_at", "updated_at")
    actions = None

    def has_delete_permission(self, request, obj=None):
        allowed = super().has_delete_permission(request, obj)
        return allowed and (obj is None or not future_working_hour_bookings(obj))

    def delete_view(self, request, object_id, extra_context=None):
        with transaction.atomic():
            hours = self.get_object(request, object_id)
            if request.method == "POST" and hours is not None:
                Doctor.objects.select_for_update().get(pk=hours.doctor_id)
            return super().delete_view(request, object_id, extra_context)
