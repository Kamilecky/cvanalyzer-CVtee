"""recruitment/models.py - Modele HR Recruitment: stanowiska, profile kandydatów, dopasowania."""

import uuid
from django.db import models
from django.conf import settings


class JobPosition(models.Model):
    """Stanowisko rekrutacyjne z wymaganiami."""

    EMPLOYMENT_TYPE_CHOICES = [
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
        ('contract', 'Contract'),
        ('remote', 'Remote'),
        ('hybrid', 'Hybrid'),
    ]

    SENIORITY_CHOICES = [
        ('intern', 'Intern'),
        ('junior', 'Junior'),
        ('mid', 'Mid-level'),
        ('senior', 'Senior'),
        ('lead', 'Lead'),
        ('principal', 'Principal'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='job_positions',
    )

    # Basic info
    title = models.CharField(max_length=255)
    department = models.CharField(max_length=100, blank=True, default='')
    location = models.CharField(max_length=255, blank=True, default='')
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, default='full_time')
    seniority_level = models.CharField(max_length=20, choices=SENIORITY_CHOICES, default='mid')

    # Requirements
    required_skills = models.JSONField(default=list, blank=True)
    optional_skills = models.JSONField(default=list, blank=True)
    years_of_experience_required = models.PositiveIntegerField(default=0)

    # Additional criteria
    industry = models.CharField(max_length=100, blank=True, default='')
    languages_required = models.JSONField(default=list, blank=True)

    # Descriptions
    responsibilities = models.TextField(blank=True, default='')
    requirements_description = models.TextField(blank=True, default='')
    nice_to_have = models.TextField(blank=True, default='')

    # Cached stats
    candidate_count = models.PositiveIntegerField(default=0)
    avg_match_score = models.FloatField(null=True, blank=True)

    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'recruitment_job_position'

    def __str__(self):
        return f"{self.title} ({self.get_seniority_level_display()})"


class CandidateProfile(models.Model):
    """Strukturalny profil kandydata wyekstrahowany z CV."""

    SENIORITY_CHOICES = JobPosition.SENIORITY_CHOICES

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='candidate_profiles',
    )
    cv_document = models.OneToOneField(
        'cv.CVDocument', on_delete=models.CASCADE,
        related_name='candidate_profile',
    )

    # Basic info
    name = models.CharField(max_length=255, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=50, blank=True, default='')
    location = models.CharField(max_length=255, blank=True, default='')

    # Experience
    years_of_experience = models.PositiveIntegerField(null=True, blank=True)
    current_role = models.CharField(max_length=255, blank=True, default='')
    seniority_level = models.CharField(max_length=20, choices=SENIORITY_CHOICES, blank=True, default='')

    # Structured data (JSON)
    skills = models.JSONField(default=list, blank=True)
    skill_levels = models.JSONField(default=dict, blank=True)
    education = models.JSONField(default=list, blank=True)
    companies = models.JSONField(default=list, blank=True)
    languages = models.JSONField(default=list, blank=True)
    certifications = models.JSONField(default=list, blank=True)

    # AI-generated
    tags = models.JSONField(default=list, blank=True)
    hr_summary = models.TextField(blank=True, default='')
    red_flags = models.JSONField(default=list, blank=True)

    # Raw AI response
    raw_extraction = models.JSONField(default=dict, blank=True)

    # Status
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ])
    error_message = models.TextField(blank=True, default='')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'recruitment_candidate_profile'

    def __str__(self):
        return self.name or f"Candidate {str(self.id)[:8]}"


class JobFitResult(models.Model):
    """Wynik dopasowania kandydata do stanowiska."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ]

    RECOMMENDATION_CHOICES = [
        ('excellent', 'Excellent'),
        ('strong_fit', 'Strong Fit'),
        ('good_fit', 'Good Fit'),
        ('moderate_fit', 'Moderate Fit'),
        ('weak_fit', 'Weak Fit'),
        ('poor', 'Poor'),
        ('not_recommended', 'Not Recommended'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='job_fit_results',
    )
    candidate = models.ForeignKey(
        CandidateProfile, on_delete=models.CASCADE,
        related_name='fit_results',
    )
    position = models.ForeignKey(
        JobPosition, on_delete=models.CASCADE,
        related_name='fit_results',
    )

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.PositiveIntegerField(default=0)

    # Match scores (0-100)
    overall_match = models.PositiveIntegerField(null=True, blank=True)
    skill_match = models.PositiveIntegerField(null=True, blank=True)
    experience_match = models.PositiveIntegerField(null=True, blank=True)
    seniority_match = models.PositiveIntegerField(null=True, blank=True)
    education_match = models.PositiveIntegerField(null=True, blank=True)

    # Detailed analysis (JSON)
    matching_skills = models.JSONField(default=list, blank=True)
    missing_skills = models.JSONField(default=list, blank=True)

    # AI features
    interview_questions = models.JSONField(default=list, blank=True)
    fit_recommendation = models.CharField(
        max_length=20, choices=RECOMMENDATION_CHOICES, blank=True, default='',
    )

    # Raw data
    raw_ai_response = models.JSONField(default=dict, blank=True)
    openai_tokens_used = models.PositiveIntegerField(default=0)
    processing_time_seconds = models.FloatField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-overall_match', '-created_at']
        unique_together = ['candidate', 'position']
        db_table = 'recruitment_job_fit_result'

    def __str__(self):
        return f"{self.candidate.name} → {self.position.title} ({self.overall_match}%)"

    def get_classification(self):
        """Klasyfikacja dopasowania na podstawie overall_match."""
        if self.overall_match is None:
            return ''
        if self.overall_match >= 90:
            return 'Excellent'
        if self.overall_match >= 75:
            return 'Strong'
        if self.overall_match >= 60:
            return 'Moderate'
        if self.overall_match >= 40:
            return 'Weak'
        return 'Poor'


class RequirementMatch(models.Model):
    """Dopasowanie pojedynczego wymagania z pozycji do CV kandydata."""

    REQUIREMENT_TYPES = [
        ('skill_required', 'Required Skill'),
        ('skill_optional', 'Optional Skill'),
        ('responsibility', 'Responsibility'),
        ('experience', 'Experience'),
        ('language', 'Language'),
    ]

    WEIGHTS = {
        'skill_required': 1.5,
        'skill_optional': 0.7,
        'responsibility': 1.2,
        'experience': 2.0,
        'language': 1.5,
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fit_result = models.ForeignKey(
        JobFitResult, on_delete=models.CASCADE,
        related_name='requirement_matches',
    )
    requirement_text = models.TextField()
    requirement_type = models.CharField(max_length=20, choices=REQUIREMENT_TYPES)
    match_percentage = models.FloatField(default=0)
    explanation = models.TextField(blank=True, default='')
    weight = models.FloatField(default=1.0)

    class Meta:
        ordering = ['-match_percentage']
        db_table = 'recruitment_requirement_match'

    def __str__(self):
        return f"{self.requirement_text[:50]} → {self.match_percentage}%"


class SectionScore(models.Model):
    """Scoring sekcji CV wzgledem stanowiska z analiza tekstowa."""

    SECTION_TYPES = [
        ('experience', 'Doswiadczenie zawodowe'),
        ('education', 'Wyksztalcenie'),
        ('languages', 'Znajomosc jezykow'),
        ('skills', 'Umiejetnosci'),
        ('interests', 'Zainteresowania'),
    ]

    SECTION_WEIGHTS = {
        'experience': 2.0,
        'skills': 2.0,
        'languages': 1.5,
        'education': 1.2,
        'interests': 0.3,
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fit_result = models.ForeignKey(
        JobFitResult, on_delete=models.CASCADE,
        related_name='section_scores',
    )
    section_name = models.CharField(max_length=50, choices=SECTION_TYPES)
    score = models.FloatField(default=0)
    weight = models.FloatField(default=1.0)
    analysis = models.TextField(blank=True, default='')
    section_content = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-score']
        db_table = 'recruitment_section_score'
        unique_together = ['fit_result', 'section_name']

    def __str__(self):
        return f"{self.get_section_name_display()} → {self.score:.0f}%"
