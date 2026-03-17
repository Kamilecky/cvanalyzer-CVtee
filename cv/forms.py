"""cv/forms.py - Formularz uploadu CV."""

from django import forms
from django.core.exceptions import ValidationError

ALLOWED_CONTENT_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB


class CVUploadForm(forms.Form):
    """Formularz przesyłania pliku CV (PDF, DOCX)."""

    file = forms.FileField(
        label='CV File',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.docx',
            'id': 'cvFileInput',
        }),
    )

    def clean_file(self):
        f = self.cleaned_data.get('file')
        if f:
            if f.size > MAX_UPLOAD_SIZE:
                raise ValidationError('File too large. Maximum size is 5 MB.')
            if f.content_type not in ALLOWED_CONTENT_TYPES:
                raise ValidationError('Invalid file type. Only PDF and DOCX files are allowed.')
        return f
