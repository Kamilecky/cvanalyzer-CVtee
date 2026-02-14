"""cv/forms.py - Formularz uploadu CV."""

from django import forms


class CVUploadForm(forms.Form):
    """Formularz przesyłania pliku CV (PDF, DOCX, TXT)."""

    file = forms.FileField(
        label='CV File',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.docx,.txt',
            'id': 'cvFileInput',
        }),
    )
