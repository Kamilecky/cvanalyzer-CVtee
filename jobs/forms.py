"""jobs/forms.py - Formularz dopasowania oferty pracy."""

from django import forms


class JobMatchForm(forms.Form):
    """Formularz wprowadzania oferty pracy do dopasowania z CV."""

    cv_id = forms.IntegerField(widget=forms.HiddenInput())
    source_type = forms.ChoiceField(
        choices=[('text', 'Paste Text'), ('url', 'Job URL')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='text',
    )
    job_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://example.com/job-posting',
        }),
    )
    job_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 8,
            'placeholder': 'Paste the job description here...',
        }),
    )
    job_title = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Job title (optional)',
        }),
    )
    company = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Company name (optional)',
        }),
    )

    def clean(self):
        cleaned_data = super().clean()
        source_type = cleaned_data.get('source_type')
        job_url = cleaned_data.get('job_url')
        job_text = cleaned_data.get('job_text')

        if source_type == 'url' and not job_url:
            self.add_error('job_url', 'Please provide a job posting URL.')
        elif source_type == 'text' and not job_text:
            self.add_error('job_text', 'Please paste the job description text.')

        return cleaned_data
