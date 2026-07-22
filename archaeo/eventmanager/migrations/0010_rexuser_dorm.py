from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eventmanager', '0009_rexevent_tags_and_config_dorms'),
    ]

    operations = [
        migrations.AddField(
            model_name='rexuser',
            name='dorm',
            field=models.CharField(
                blank=True,
                default='',
                help_text='For area directors, the dorm whose events they may approve.',
                max_length=40,
            ),
        ),
    ]
