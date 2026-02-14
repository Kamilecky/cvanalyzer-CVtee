"""analysis/admin.py - Konfiguracja panelu admin dla modeli analizy."""

from django.contrib import admin
from .models import AnalysisResult, Problem, Recommendation, RewrittenSection, SkillGap, SectionAnalysis


class ProblemInline(admin.TabularInline):
    model = Problem
    extra = 0


class RecommendationInline(admin.TabularInline):
    model = Recommendation
    extra = 0


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'cv_document', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__email', 'cv_document__original_filename']
    readonly_fields = ['id', 'created_at', 'completed_at', 'processing_time_seconds', 'openai_tokens_used']
    inlines = [ProblemInline, RecommendationInline]


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ['title', 'analysis', 'category', 'severity']
    list_filter = ['category', 'severity']


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ['title', 'analysis', 'recommendation_type', 'priority']
    list_filter = ['recommendation_type', 'priority']


@admin.register(RewrittenSection)
class RewrittenSectionAdmin(admin.ModelAdmin):
    list_display = ['analysis', 'section_type', 'created_at']
    list_filter = ['section_type']


@admin.register(SkillGap)
class SkillGapAdmin(admin.ModelAdmin):
    list_display = ['skill_name', 'analysis', 'importance']
    list_filter = ['importance']


@admin.register(SectionAnalysis)
class SectionAnalysisAdmin(admin.ModelAdmin):
    list_display = ['section', 'status', 'analysis']
    list_filter = ['status', 'section']
    search_fields = ['analysis_text']
