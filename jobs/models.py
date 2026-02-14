"""jobs/models.py - Modele dopasowania CV do ofert pracy."""

import uuid
from django.db import models
from django.conf import settings


class JobPosting(models.Model):
    """Oferta pracy - źródło do dopasowania z CV."""

    SOURCE_CHOICES = [
        ('url', 'URL'),
        ('text', 'Pasted Text'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='job_postings', null=True, blank=True,
    )
    source_type = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    source_url = models.URLField(blank=True, default='')
    title = models.CharField(max_length=255, blank=True, default='')
    company = models.CharField(max_length=255, blank=True, default='')
    raw_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'jobs_posting'

    def __str__(self):
        return self.title or self.source_url or f'Job #{self.id}'


class MatchResult(models.Model):
    """Wynik dopasowania CV do oferty pracy."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='match_results', null=True, blank=True,
    )
    cv_document = models.ForeignKey(
        'cv.CVDocument', on_delete=models.CASCADE, related_name='match_results',
    )
    job_posting = models.ForeignKey(
        JobPosting, on_delete=models.CASCADE, related_name='match_results',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    match_percentage = models.PositiveIntegerField(null=True, blank=True)
    matching_skills = models.JSONField(default=list, blank=True)
    missing_skills = models.JSONField(default=list, blank=True)
    keyword_matches = models.JSONField(default=list, blank=True)
    missing_keywords = models.JSONField(default=list, blank=True)
    strengths = models.JSONField(default=list, blank=True)
    weaknesses = models.JSONField(default=list, blank=True)
    recommendations = models.JSONField(default=list, blank=True)
    summary = models.TextField(blank=True, default='')
    raw_ai_response = models.JSONField(default=dict, blank=True)

    celery_task_id = models.CharField(max_length=255, blank=True, default='')
    openai_tokens_used = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'jobs_match_result'

    def __str__(self):
        return f'Match {self.id} - {self.match_percentage or "?"}%'
