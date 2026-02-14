"""recruitment/forms.py - Formularze modułu rekrutacji."""

from django import forms
from .models import JobPosition


class JobPositionForm(forms.ModelForm):
    """Formularz tworzenia/edycji stanowiska rekrutacyjnego."""

    required_skills_text = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3, 'class': 'form-control',
            'placeholder': 'Python, Django, SQL (comma-separated)',
        }),
        required=False,
        label='Required Skills',
    )

    optional_skills_text = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 2, 'class': 'form-control',
            'placeholder': 'React, Docker, AWS (comma-separated)',
        }),
        required=False,
        label='Optional Skills',
    )

    languages_required_text = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 2, 'class': 'form-control',
            'placeholder': 'English: Fluent\nPolish: Native',
        }),
        required=False,
        label='Required Languages',
    )

    class Meta:
        model = JobPosition
        fields = [
            'title', 'department', 'location', 'employment_type', 'seniority_level',
            'years_of_experience_required', 'industry',
            'responsibilities', 'requirements_description', 'nice_to_have',
            'is_active',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'employment_type': forms.Select(attrs={'class': 'form-select'}),
            'seniority_level': forms.Select(attrs={'class': 'form-select'}),
            'years_of_experience_required': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'industry': forms.TextInput(attrs={'class': 'form-control'}),
            'responsibilities': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'requirements_description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'nice_to_have': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['required_skills_text'].initial = ', '.join(self.instance.required_skills or [])
            self.fields['optional_skills_text'].initial = ', '.join(self.instance.optional_skills or [])
            self.fields['languages_required_text'].initial = '\n'.join(self.instance.languages_required or [])

    def save(self, commit=True):
        instance = super().save(commit=False)
        req = self.cleaned_data.get('required_skills_text', '')
        instance.required_skills = [s.strip() for s in req.split(',') if s.strip()] if req else []
        opt = self.cleaned_data.get('optional_skills_text', '')
        instance.optional_skills = [s.strip() for s in opt.split(',') if s.strip()] if opt else []
        lang = self.cleaned_data.get('languages_required_text', '')
        instance.languages_required = [l.strip() for l in lang.split('\n') if l.strip()] if lang else []
        if commit:
            instance.save()
        return instance


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.docx,.txt',
        }))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single = super().clean
        if isinstance(data, (list, tuple)):
            return [single(d, initial) for d in data]
        return [single(data, initial)]


class BulkUploadForm(forms.Form):
    """Formularz bulk uploadu CV."""

    cv_files = MultipleFileField(label='CV Files')


class CVUploadForm(forms.Form):
    """Formularz uploadu CV: pojedyncze lub wiele plikow naraz."""

    single_cv = forms.FileField(
        required=False,
        label='Single CV',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.docx,.txt',
        }),
    )
    multiple_cvs = MultipleFileField(
        required=False,
        label='Multiple CVs',
    )

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('single_cv') and not cleaned_data.get('multiple_cvs'):
            raise forms.ValidationError('Upload at least one CV file.')
        return cleaned_data
