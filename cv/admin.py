"""cv/admin.py - Panel admina dla modeli CV."""

from django.contrib import admin
from .models import CVDocument, CVVersion, CVSection


@admin.register(CVDocument)
class CVDocumentAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'user', 'file_format', 'file_size', 'is_active', 'uploaded_at')
    list_filter = ('file_format', 'is_active')
    search_fields = ('original_filename', 'user__email')


@admin.register(CVVersion)
class CVVersionAdmin(admin.ModelAdmin):
    list_display = ('document', 'version_number', 'file_size', 'created_at')


@admin.register(CVSection)
class CVSectionAdmin(admin.ModelAdmin):
    list_display = ('document', 'section_type', 'title', 'order')
    list_filter = ('section_type',)
