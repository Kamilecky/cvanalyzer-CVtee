"""
cv/models.py - Modele danych aplikacji CV.

Zawiera:
- CVDocument: Dokument CV przesłany przez użytkownika (PDF/DOCX/TXT).
- CVVersion: Historia wersji dokumentu CV.
- CVSection: Wykryta sekcja w dokumencie CV (doświadczenie, edukacja, umiejętności itp.).
"""

import uuid
from django.db import models
from django.conf import settings


def cv_upload_path(instance, filename):
    """Generuje ścieżkę uploadu izolowaną per-użytkownik z UUID."""
    user_id = instance.user.id if instance.user else 'guest'
    return f'cvs/{user_id}/{uuid.uuid4().hex}_{filename}'


class CVDocument(models.Model):
    """Dokument CV przesłany przez użytkownika."""

    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('docx', 'DOCX'),
        ('txt', 'TXT'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='cv_documents', null=True, blank=True,
    )
    title = models.CharField(max_length=255, blank=True, default='')
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to=cv_upload_path)
    file_format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    file_size = models.PositiveIntegerField(default=0)
    extracted_text = models.TextField(blank=True, default='')
    file_hash = models.CharField(max_length=64, blank=True, default='', db_index=True)
    is_active = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    guest_session = models.ForeignKey(
        'accounts.GuestSession', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='cv_documents',
    )

    class Meta:
        ordering = ['-uploaded_at']
        db_table = 'cv_document'

    def __str__(self):
        return f'{self.original_filename} ({self.user.email if self.user else "guest"})'

    def get_file_size_display(self):
        """Formatuje rozmiar pliku (B/KB/MB)."""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} TB'

    @property
    def latest_analysis(self):
        return self.analyses.order_by('-created_at').first()


class CVVersion(models.Model):
    """Historia wersji dokumentu CV."""

    document = models.ForeignKey(CVDocument, on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField()
    file = models.FileField(upload_to=cv_upload_path)
    extracted_text = models.TextField(blank=True, default='')
    file_size = models.PositiveIntegerField(default=0)
    changelog = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_number']
        unique_together = ['document', 'version_number']
        db_table = 'cv_version'

    def __str__(self):
        return f'{self.document.original_filename} v{self.version_number}'


class CVSection(models.Model):
    """Wykryta sekcja w dokumencie CV."""

    SECTION_TYPES = [
        ('summary', 'Summary / Profile'),
        ('experience', 'Work Experience'),
        ('education', 'Education'),
        ('skills', 'Skills'),
        ('projects', 'Projects'),
        ('certificates', 'Certificates'),
        ('languages', 'Languages'),
        ('contact', 'Contact'),
        ('interests', 'Interests'),
        ('other', 'Other'),
    ]

    document = models.ForeignKey(CVDocument, on_delete=models.CASCADE, related_name='sections')
    section_type = models.CharField(max_length=30, choices=SECTION_TYPES)
    title = models.CharField(max_length=255)
    content = models.TextField()
    start_position = models.PositiveIntegerField(default=0)
    end_position = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        db_table = 'cv_section'

    def __str__(self):
        return f'{self.get_section_type_display()}: {self.title[:50]}'
