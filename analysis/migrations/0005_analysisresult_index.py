from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analysis', '0004_alter_analysisresult_status'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='analysisresult',
            index=models.Index(fields=['user', 'created_at'], name='analysis_user_created_idx'),
        ),
    ]
