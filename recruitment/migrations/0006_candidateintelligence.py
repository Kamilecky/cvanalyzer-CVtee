"""recruitment/migrations/0006_candidateintelligence.py

Adds CandidateIntelligence model — AI intelligence layer for Premium/Enterprise.
"""

import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recruitment', '0005_positionweighttemplate'),
    ]

    operations = [
        migrations.CreateModel(
            name='CandidateIntelligence',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('skill_fit', models.JSONField(blank=True, default=dict)),
                ('learnability', models.JSONField(blank=True, default=dict)),
                ('career_trajectory', models.JSONField(blank=True, default=dict)),
                ('behavioral_signals', models.JSONField(blank=True, default=list)),
                ('risk_flags', models.JSONField(blank=True, default=list)),
                ('confidence', models.CharField(choices=[('high', 'High'), ('medium', 'Medium'), ('low', 'Low')], default='medium', max_length=10)),
                ('recommendation', models.CharField(choices=[('invite', 'Invite'), ('consider', 'Consider'), ('reject', 'Reject')], default='consider', max_length=10)),
                ('recommendation_reason', models.TextField(blank=True, default='')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('done', 'Done'), ('failed', 'Failed')], default='pending', max_length=10)),
                ('error_message', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('profile', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='intelligence',
                    to='recruitment.candidateprofile',
                )),
            ],
            options={
                'db_table': 'recruitment_candidate_intelligence',
            },
        ),
    ]
