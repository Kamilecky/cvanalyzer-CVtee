"""recruitment/services/interview_generator.py - Generowanie pytań rekrutacyjnych AI."""

import json
import logging

from analysis.services.openai_client import OpenAIClient
from .prompts import SYSTEM_PROMPT, INTERVIEW_QUESTIONS_PROMPT

logger = logging.getLogger(__name__)


class InterviewGenerator:
    """Generuje pytania rekrutacyjne na podstawie profilu i stanowiska."""

    def __init__(self):
        self.client = OpenAIClient()

    def generate_questions(self, job_fit_result):
        """Generuje 5-8 pytań rekrutacyjnych dla JobFitResult.

        Returns:
            list of question dicts
        """
        try:
            profile = job_fit_result.candidate
            position = job_fit_result.position

            profile_summary = json.dumps({
                'current_role': profile.current_role,
                'years_experience': profile.years_of_experience,
                'skills': profile.skills[:10],
                'recent_companies': [c.get('company', '') for c in profile.companies[:3]],
            })

            missing_skills = ', '.join(job_fit_result.missing_skills[:5]) or 'None'

            prompt = INTERVIEW_QUESTIONS_PROMPT.format(
                candidate_name=profile.name,
                profile_summary=profile_summary,
                position_title=position.title,
                missing_skills=missing_skills,
            )

            result = self.client.chat(SYSTEM_PROMPT, prompt)
            if result['error']:
                raise Exception(f"OpenAI API error: {result['error']}")

            data = self.client.parse_json_response(result['content'])
            if not data or 'questions' not in data:
                raise Exception("Failed to parse interview questions")

            questions = data['questions']

            # Validation: dedup, limit, minimum check
            questions = self._validate_questions(questions)

            # Retry once if too few questions
            if len(questions) < 3:
                logger.warning(f"Only {len(questions)} questions, retrying once...")
                retry_result = self.client.chat(SYSTEM_PROMPT, prompt)
                if not retry_result['error']:
                    retry_data = self.client.parse_json_response(retry_result['content'])
                    if retry_data and 'questions' in retry_data:
                        questions = self._validate_questions(retry_data['questions'])

            job_fit_result.interview_questions = questions
            job_fit_result.save(update_fields=['interview_questions'])

            logger.info(
                f"Generated {len(questions)} questions for "
                f"{profile.name} → {position.title}"
            )
            return questions

        except Exception as e:
            logger.error(f"Interview question generation failed: {e}")
            return []

    @staticmethod
    def _validate_questions(questions):
        """Dedup, limit max 10, remove empty."""
        seen = set()
        unique = []
        for q in questions:
            # Support both dict and string questions
            q_text = q.get('question', '') if isinstance(q, dict) else str(q)
            if q_text and q_text not in seen:
                seen.add(q_text)
                unique.append(q)
        return unique[:10]
