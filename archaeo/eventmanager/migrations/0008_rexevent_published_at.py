from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("eventmanager", "0007_site_config_and_form_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="rexevent",
            name="published_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
