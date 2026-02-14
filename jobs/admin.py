"""jobs/admin.py - Konfiguracja panelu admin dla modeli ofert pracy."""

from django.contrib import admin
from .models import JobPosting, MatchResult


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'source_type', 'user', 'created_at']
    list_filter = ['source_type', 'created_at']
    search_fields = ['title', 'company', 'user__email']


@admin.register(MatchResult)
class MatchResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'cv_document', 'job_posting', 'match_percentage', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__email']
    readonly_fields = ['id', 'created_at', 'completed_at']
