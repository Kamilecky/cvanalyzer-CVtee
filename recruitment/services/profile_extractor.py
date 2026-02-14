"""recruitment/services/profile_extractor.py - CV → CandidateProfile extraction."""

import logging
import time

from recruitment.models import CandidateProfile
from analysis.services.openai_client import OpenAIClient
from analysis.services.text_cleaner import TextCleaner
from .prompts import SYSTEM_PROMPT, PROFILE_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class ProfileExtractor:
    """Wyciąga strukturalny profil kandydata z tekstu CV."""

    def __init__(self):
        self.client = OpenAIClient()

    def extract_profile(self, cv_document, user):
        """Ekstrakcja CandidateProfile z CVDocument.

        Returns:
            CandidateProfile instance
        """
        profile, created = CandidateProfile.objects.get_or_create(
            cv_document=cv_document,
            defaults={'user': user},
        )

        profile.status = 'processing'
        profile.save(update_fields=['status'])

        start_time = time.time()

        try:
            cv_text = cv_document.extracted_text
            if not cv_text:
                raise ValueError("CV has no extracted text")

            cleaned_text = TextCleaner.clean(cv_text, max_length=4000)

            prompt = PROFILE_EXTRACTION_PROMPT.format(cv_text=cleaned_text)
            result = self.client.chat(SYSTEM_PROMPT, prompt)

            if result['error']:
                raise Exception(f"OpenAI API error: {result['error']}")

            data = self.client.parse_json_response(result['content'])
            if not data or 'profile' not in data:
                raise Exception("Failed to parse extraction response")

            p = data['profile']
            profile.name = p.get('name', '')[:255]
            profile.email = p.get('email', '')[:254]
            profile.phone = p.get('phone', '')[:50]
            profile.location = p.get('location', '')[:255]
            profile.current_role = p.get('current_role', '')[:255]
            profile.years_of_experience = p.get('years_of_experience')
            profile.seniority_level = p.get('seniority_level', '')[:20]
            profile.skills = p.get('skills', [])
            profile.skill_levels = p.get('skill_levels', {})
            profile.education = p.get('education', [])
            profile.companies = p.get('companies', [])
            profile.languages = p.get('languages', [])
            profile.certifications = p.get('certifications', [])

            profile.hr_summary = data.get('hr_summary', '')
            profile.red_flags = data.get('red_flags', [])
            profile.tags = data.get('tags', [])
            profile.raw_extraction = data

            profile.status = 'done'
            profile.error_message = ''
            profile.save()

            logger.info(
                f"Profile extraction for CV {cv_document.id} completed in "
                f"{time.time() - start_time:.1f}s: {profile.name}"
            )
            return profile

        except Exception as e:
            logger.error(f"Profile extraction failed for CV {cv_document.id}: {e}")
            profile.status = 'failed'
            profile.error_message = str(e)
            profile.save(update_fields=['status', 'error_message'])
            return profile
