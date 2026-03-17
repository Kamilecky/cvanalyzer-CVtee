from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analysis', '0005_analysisresult_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='analysisresult',
            name='security_flags',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
