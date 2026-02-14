"""jobs/services/matcher.py - Dopasowanie CV do oferty pracy przez AI."""

import logging
import time
from django.utils import timezone

from jobs.models import MatchResult
from analysis.services.openai_client import OpenAIClient
from analysis.services.prompts import SYSTEM_PROMPT, JOB_MATCH_PROMPT

logger = logging.getLogger(__name__)


class JobMatcher:
    """Porównuje CV z ofertą pracy używając OpenAI GPT."""

    def __init__(self):
        self.client = OpenAIClient()

    def run_match(self, match_id):
        """Uruchamia dopasowanie CV do oferty pracy.

        Args:
            match_id: UUID obiektu MatchResult

        Returns:
            MatchResult po zaktualizowaniu wyników
        """
        match = MatchResult.objects.select_related('cv_document', 'job_posting').get(id=match_id)
        match.status = 'processing'
        match.save(update_fields=['status'])

        start_time = time.time()

        try:
            cv_text = match.cv_document.extracted_text
            job_text = match.job_posting.raw_text

            if not cv_text or not job_text:
                raise ValueError("Missing CV or job posting text")

            prompt = JOB_MATCH_PROMPT.format(
                cv_text=cv_text[:6000],
                job_text=job_text[:6000],
            )

            result = self.client.chat(SYSTEM_PROMPT, prompt)
            if result['error']:
                raise Exception(f"OpenAI API error: {result['error']}")

            data = self.client.parse_json_response(result['content'])
            if not data:
                raise Exception("Failed to parse AI response")

            match.match_percentage = max(0, min(100, int(data.get('match_percentage', 0))))
            match.matching_skills = data.get('matching_skills', [])
            match.missing_skills = data.get('missing_skills', [])
            match.keyword_matches = data.get('keyword_matches', [])
            match.missing_keywords = data.get('missing_keywords', [])
            match.strengths = data.get('strengths', [])
            match.weaknesses = data.get('weaknesses', [])
            match.recommendations = data.get('recommendations', [])
            match.summary = data.get('summary', '')
            match.raw_ai_response = data
            match.openai_tokens_used = result['tokens_used']
            match.status = 'done'
            match.completed_at = timezone.now()
            match.error_message = ''
            match.save()

            return match

        except Exception as e:
            logger.error(f"Job match {match_id} failed: {e}")
            match.status = 'failed'
            match.error_message = str(e)
            match.save(update_fields=['status', 'error_message'])
            return match
