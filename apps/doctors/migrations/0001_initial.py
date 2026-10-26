import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="Doctor",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("first_name", models.CharField(max_length=100)),
                ("last_name", models.CharField(max_length=100)),
                ("is_active", models.BooleanField(default=True)),
                ("user", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="doctor_profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["first_name", "last_name", "id"]},
        ),
        migrations.CreateModel(
            name="WorkingHour",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("weekday", models.PositiveSmallIntegerField(choices=[(0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"), (4, "Friday"), (5, "Saturday"), (6, "Sunday")])),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("doctor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="working_hours", to="doctors.doctor")),
            ],
            options={
                "ordering": ["weekday", "start_time"],
                "constraints": [
                    models.UniqueConstraint(fields=("doctor", "weekday"), name="unique_doctor_weekday"),
                    models.CheckConstraint(condition=models.Q(end_time__gt=models.F("start_time")), name="working_hours_end_after_start"),
                    models.CheckConstraint(condition=models.Q(weekday__gte=0, weekday__lte=6), name="working_hours_valid_weekday"),
                ],
            },
        ),
    ]
