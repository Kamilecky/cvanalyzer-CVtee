"""recruitment/admin.py - Konfiguracja panelu administracyjnego."""

from django.contrib import admin
from .models import JobPosition, CandidateProfile, JobFitResult, RequirementMatch, SectionScore


@admin.register(JobPosition)
class JobPositionAdmin(admin.ModelAdmin):
    list_display = ['title', 'seniority_level', 'employment_type', 'candidate_count', 'avg_match_score', 'is_active', 'created_at']
    list_filter = ['seniority_level', 'employment_type', 'is_active']
    search_fields = ['title', 'department', 'location']
    readonly_fields = ['id', 'candidate_count', 'avg_match_score', 'created_at', 'updated_at']


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'current_role', 'seniority_level', 'years_of_experience', 'status', 'created_at']
    list_filter = ['seniority_level', 'status']
    search_fields = ['name', 'email', 'current_role']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(JobFitResult)
class JobFitResultAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'position', 'overall_match', 'skill_match', 'fit_recommendation', 'status', 'created_at']
    list_filter = ['status', 'fit_recommendation']
    search_fields = ['candidate__name', 'position__title']
    readonly_fields = ['id', 'created_at', 'completed_at']


@admin.register(RequirementMatch)
class RequirementMatchAdmin(admin.ModelAdmin):
    list_display = ['requirement_text_short', 'requirement_type', 'match_percentage', 'weight', 'fit_result']
    list_filter = ['requirement_type']
    search_fields = ['requirement_text', 'explanation']
    readonly_fields = ['id']

    def requirement_text_short(self, obj):
        return obj.requirement_text[:60] + '...' if len(obj.requirement_text) > 60 else obj.requirement_text
    requirement_text_short.short_description = 'Requirement'


@admin.register(SectionScore)
class SectionScoreAdmin(admin.ModelAdmin):
    list_display = ['section_name', 'score', 'weight', 'fit_result']
    list_filter = ['section_name']
    search_fields = ['analysis']
    readonly_fields = ['id']
