from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("doctors", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="doctor",
            name="specialization",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
    ]
