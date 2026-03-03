"""Migration: add PositionWeightTemplate model."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('recruitment', '0004_alter_candidateprofile_status_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PositionWeightTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('w_experience', models.FloatField(default=5.0)),
                ('w_education', models.FloatField(default=3.0)),
                ('w_certifications', models.FloatField(default=2.0)),
                ('w_hard_skills', models.FloatField(default=5.0)),
                ('w_soft_skills', models.FloatField(default=2.0)),
                ('w_languages', models.FloatField(default=3.0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('position', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='weight_template',
                    to='recruitment.jobposition',
                )),
            ],
            options={
                'db_table': 'recruitment_position_weight_template',
            },
        ),
    ]
