"""reports/models.py - Modele generowania raportów PDF."""

import uuid
from django.db import models
from django.conf import settings


def report_upload_path(instance, filename):
    user_id = instance.user.id if instance.user else 'guest'
    return f'reports/{user_id}/{uuid.uuid4().hex}_{filename}'


class Report(models.Model):
    """Wygenerowany raport PDF z wynikami analizy."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='reports',
    )
    analysis = models.ForeignKey(
        'analysis.AnalysisResult', on_delete=models.CASCADE,
        related_name='reports',
    )
    file = models.FileField(upload_to=report_upload_path, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    celery_task_id = models.CharField(max_length=255, blank=True, default='')
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'reports_report'

    def __str__(self):
        return f'Report {self.id} ({self.status})'
