"""recruitment/services/profile_extractor.py - CV → CandidateProfile extraction."""

import logging
import re
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

            # Fill missing name/email from regex if AI didn't provide them
            if not profile.name or not profile.email:
                basic = self._extract_basic_info(cv_text)
                if not profile.name and basic['name']:
                    profile.name = basic['name']
                if not profile.email and basic['email']:
                    profile.email = basic['email']
                if not profile.phone and basic['phone']:
                    profile.phone = basic['phone']

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
            # Regex fallback — partial profile
            cv_text = cv_document.extracted_text or ''
            if cv_text:
                basic = self._extract_basic_info(cv_text)
                profile.name = basic.get('name', '')[:255]
                profile.email = basic.get('email', '')[:254]
                profile.phone = basic.get('phone', '')[:50]
                profile.status = 'partial'
                profile.error_message = f'AI failed, regex fallback used: {e}'
                profile.save()
                logger.info(f"Profile {cv_document.id}: partial via regex fallback")
            else:
                profile.status = 'failed'
                profile.error_message = str(e)
                profile.save(update_fields=['status', 'error_message'])
            return profile

    @staticmethod
    def _extract_basic_info(text):
        """Regex fallback: wyciąga email, phone, name z surowego tekstu CV."""
        result = {'email': '', 'phone': '', 'name': ''}

        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if email_match:
            result['email'] = email_match.group()

        phone_match = re.search(r'[\+]?[\d\s\-\(\)]{7,15}', text)
        if phone_match:
            candidate = phone_match.group().strip()
            digits = re.sub(r'\D', '', candidate)
            if 7 <= len(digits) <= 15:
                result['phone'] = candidate

        for line in text.split('\n'):
            line = line.strip()
            if line and len(line) < 60 and not re.search(r'[@\d]', line):
                result['name'] = line
                break

        return result
