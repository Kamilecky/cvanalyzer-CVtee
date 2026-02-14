"""
analysis/models.py - Modele analizy AI CV.

Zawiera: AnalysisResult, Problem, Recommendation, RewrittenSection, SkillGap.
"""

import uuid
from django.db import models
from django.conf import settings


class AnalysisResult(models.Model):
    """Wynik analizy AI dla dokumentu CV."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='analyses', null=True, blank=True,
    )
    cv_document = models.ForeignKey(
        'cv.CVDocument', on_delete=models.CASCADE, related_name='analyses',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.PositiveIntegerField(default=0)

    # Qualitative analysis (no numerical scores)
    summary = models.TextField(blank=True, default='')

    sections_detected = models.JSONField(default=list, blank=True)
    raw_ai_response = models.JSONField(default=dict, blank=True)
    percentile_rank = models.PositiveIntegerField(null=True, blank=True)

    celery_task_id = models.CharField(max_length=255, blank=True, default='')
    processing_time_seconds = models.FloatField(null=True, blank=True)
    openai_tokens_used = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    guest_session = models.ForeignKey(
        'accounts.GuestSession', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='analyses',
    )

    class Meta:
        ordering = ['-created_at']
        db_table = 'analysis_result'

    def __str__(self):
        return f'Analysis {self.id} - {self.status}'


class Problem(models.Model):
    """Problem wykryty w CV."""

    SEVERITY_CHOICES = [
        ('critical', 'Critical'),
        ('warning', 'Warning'),
        ('info', 'Info'),
    ]
    CATEGORY_CHOICES = [
        ('generic_description', 'Too Generic Descriptions'),
        ('missing_specifics', 'Missing Specifics'),
        ('missing_keywords', 'Missing Keywords'),
        ('structural', 'Structural Issues'),
        ('formatting', 'Formatting Issues'),
        ('grammar', 'Grammar / Language'),
        ('length', 'Length Issues'),
        ('other', 'Other'),
    ]

    analysis = models.ForeignKey(AnalysisResult, on_delete=models.CASCADE, related_name='problems')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='warning')
    title = models.CharField(max_length=255)
    description = models.TextField()
    section = models.CharField(max_length=50, blank=True, default='')
    affected_text = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['severity', 'category']
        db_table = 'analysis_problem'


class Recommendation(models.Model):
    """Rekomendacja AI do poprawy CV."""

    TYPE_CHOICES = [
        ('add', 'Add'),
        ('remove', 'Remove'),
        ('rewrite', 'Rewrite'),
        ('skill', 'Develop Skill'),
        ('structure', 'Restructure'),
        ('career', 'Career Advice'),
    ]
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]

    analysis = models.ForeignKey(AnalysisResult, on_delete=models.CASCADE, related_name='recommendations')
    recommendation_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    title = models.CharField(max_length=255)
    description = models.TextField()
    section = models.CharField(max_length=50, blank=True, default='')
    suggested_text = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['priority']
        db_table = 'analysis_recommendation'


class RewrittenSection(models.Model):
    """Przepisana sekcja CV przez AI (funkcja Premium)."""

    analysis = models.ForeignKey(AnalysisResult, on_delete=models.CASCADE, related_name='rewrites')
    section_type = models.CharField(max_length=30)
    original_text = models.TextField()
    rewritten_text = models.TextField()
    improvement_notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'analysis_rewritten_section'


class SkillGap(models.Model):
    """Brakująca kompetencja wykryta w analizie."""

    analysis = models.ForeignKey(AnalysisResult, on_delete=models.CASCADE, related_name='skill_gaps')
    skill_name = models.CharField(max_length=255)
    current_level = models.CharField(max_length=50, blank=True, default='')
    recommended_level = models.CharField(max_length=50, blank=True, default='')
    importance = models.CharField(max_length=20, default='medium')
    learning_resources = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'analysis_skill_gap'


class SectionAnalysis(models.Model):
    """Jakosciowa analiza pojedynczej sekcji CV."""

    STATUS_CHOICES = [
        ('present', 'Present'),
        ('missing', 'Missing'),
        ('weak', 'Weak'),
    ]

    analysis = models.ForeignKey(AnalysisResult, on_delete=models.CASCADE, related_name='section_analyses')
    section = models.CharField(max_length=50)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    analysis_text = models.TextField(blank=True, default='')
    suggestions = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['section']
        db_table = 'analysis_section_analysis'
