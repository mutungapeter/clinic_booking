from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Patient, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at")
    search_fields = ("user__username", "user__first_name", "user__last_name")
    autocomplete_fields = ("user",)
    readonly_fields = ("id", "created_at", "updated_at")
