"""reports/admin.py - Konfiguracja panelu admin dla modeli raportów."""

from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'analysis', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__email']
    readonly_fields = ['id', 'created_at']
