from django.db import migrations, models


def normalize_legacy_dorm_names(apps, schema_editor):
    RexEvent = apps.get_model("eventmanager", "RexEvent")
    RexEvent.objects.filter(dorm="Burton-Conner").update(dorm="Burton-Conner House")
    RexEvent.objects.filter(dorm="MacGregor").update(dorm="MacGregor House")


class Migration(migrations.Migration):

    dependencies = [
        ("eventmanager", "0008_rexevent_published_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="rexevent",
            name="tags",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AlterField(
            model_name="rexevent",
            name="dorm",
            field=models.CharField(max_length=40),
        ),
        migrations.AlterField(
            model_name="rexevent",
            name="dorm_sub",
            field=models.CharField(max_length=30),
        ),
        migrations.RunPython(normalize_legacy_dorm_names, migrations.RunPython.noop),
    ]
