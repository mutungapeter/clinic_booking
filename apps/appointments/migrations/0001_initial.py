import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("accounts", "0001_initial"), ("doctors", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="Appointment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("starts_at", models.DateTimeField()),
                ("status", models.CharField(choices=[("BOOKED", "Booked"), ("CANCELLED", "Cancelled")], default="BOOKED", max_length=10)),
                ("cancellation_reason", models.TextField(blank=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("doctor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="appointments", to="doctors.doctor")),
                ("patient", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="appointments", to="accounts.patient")),
            ],
            options={
                "ordering": ["starts_at", "id"],
                "indexes": [
                    models.Index(fields=["patient", "status", "starts_at"], name="patient_upcoming_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(condition=models.Q(status="BOOKED"), fields=("doctor", "starts_at"), name="unique_booked_doctor_slot"),
                    models.CheckConstraint(condition=models.Q(status__in=["BOOKED", "CANCELLED"]), name="appointment_valid_status"),
                ],
            },
        ),
    ]
