"""recruitment/services/position_matcher.py - Batch matching engine.

Optymalizacja: 1 request OpenAI = WSZYSTKIE stanowiska naraz (do 10 w batchu).
Fallback: single match dla >10 stanowisk (dzieli na chunki).
"""

import json
import logging
import time
from django.db.models import Avg, Count
from django.utils import timezone

from recruitment.models import JobPosition, JobFitResult
from analysis.services.openai_client import OpenAIClient
from .prompts import SYSTEM_PROMPT, BATCH_MATCH_PROMPT, POSITION_MATCH_PROMPT
from .requirement_matcher import analyze_cv_against_position
from .section_scorer import score_sections

logger = logging.getLogger(__name__)

MAX_BATCH_SIZE = 10


class PositionMatcher:
    """Dopasowuje CandidateProfile do wielu JobPosition w jednym zapytaniu AI."""

    def __init__(self):
        self.client = OpenAIClient()

    def match_all_positions(self, candidate_profile, user):
        """Matching kandydata do WSZYSTKICH aktywnych stanowisk."""
        positions = list(JobPosition.objects.filter(user=user, is_active=True))
        return self._run_batch_matching(positions, candidate_profile, user, skip_done=True)

    def match_selected_positions(self, candidate_profile, user, position_ids):
        """Matching kandydata do WYBRANYCH stanowisk (reset istniejacych)."""
        positions = list(JobPosition.objects.filter(
            id__in=position_ids, user=user, is_active=True,
        ))
        return self._run_batch_matching(positions, candidate_profile, user, skip_done=False)

    def _run_batch_matching(self, positions, candidate_profile, user, skip_done=True):
        """Wspolna logika batch matchingu."""
        if not positions:
            return []

        fits = {}
        for position in positions:
            fit, created = JobFitResult.objects.get_or_create(
                candidate=candidate_profile,
                position=position,
                defaults={'user': user, 'status': 'pending'},
            )
            if not created and skip_done and fit.status == 'done':
                continue
            if not created:
                fit.status = 'pending'
                fit.save(update_fields=['status'])
            fits[str(position.id)] = fit

        if not fits:
            return []

        for fit in fits.values():
            fit.status = 'processing'
            fit.progress = 10
            fit.save(update_fields=['status', 'progress'])

        profile_json = json.dumps({
            'name': candidate_profile.name,
            'current_role': candidate_profile.current_role,
            'years_of_experience': candidate_profile.years_of_experience,
            'seniority_level': candidate_profile.seniority_level,
            'skills': candidate_profile.skills,
            'skill_levels': candidate_profile.skill_levels,
            'education': candidate_profile.education,
            'companies': candidate_profile.companies[:5],
            'languages': candidate_profile.languages,
        }, indent=2)

        positions_to_match = [p for p in positions if str(p.id) in fits]
        results = []

        for i in range(0, len(positions_to_match), MAX_BATCH_SIZE):
            chunk = positions_to_match[i:i + MAX_BATCH_SIZE]
            chunk_results = self._match_batch(
                profile_json, chunk, fits, candidate_profile,
            )
            results.extend(chunk_results)

        return results

    def _match_batch(self, profile_json, positions, fits, candidate_profile):
        """1 zapytanie AI = matching vs wiele stanowisk naraz."""
        start_time = time.time()

        positions_data = []
        for p in positions:
            positions_data.append({
                'id': str(p.id),
                'title': p.title,
                'department': p.department,
                'seniority_level': p.seniority_level,
                'required_skills': p.required_skills,
                'optional_skills': p.optional_skills,
                'years_of_experience_required': p.years_of_experience_required,
                'requirements_description': p.requirements_description[:300],
            })

        positions_json = json.dumps(positions_data, indent=2)

        # Progress 40%
        for p in positions:
            pid = str(p.id)
            if pid in fits:
                fits[pid].progress = 40
                fits[pid].save(update_fields=['progress'])

        try:
            prompt = BATCH_MATCH_PROMPT.format(
                profile_json=profile_json,
                positions_json=positions_json,
            )

            result = self.client.chat(SYSTEM_PROMPT, prompt)
            if result['error']:
                raise Exception(f"OpenAI API error: {result['error']}")

            data = self.client.parse_json_response(result['content'])
            if not data or 'matches' not in data:
                raise Exception("Failed to parse batch matching response")

            # Progress 80%
            for p in positions:
                pid = str(p.id)
                if pid in fits:
                    fits[pid].progress = 80
                    fits[pid].save(update_fields=['progress'])

            elapsed = time.time() - start_time
            tokens_per_match = result['tokens_used'] // max(len(positions), 1)

            updated = []
            for match_data in data['matches']:
                pos_id = match_data.get('position_id', '')
                if pos_id not in fits:
                    continue

                fit = fits[pos_id]
                scores = match_data.get('scores', {})
                fit.overall_match = self._clamp(scores.get('overall_match'))
                fit.skill_match = self._clamp(scores.get('skill_match'))
                fit.experience_match = self._clamp(scores.get('experience_match'))
                fit.seniority_match = self._clamp(scores.get('seniority_match'))
                fit.education_match = self._clamp(scores.get('education_match'))

                fit.matching_skills = match_data.get('matching_skills', [])
                fit.missing_skills = match_data.get('missing_skills', [])
                fit.fit_recommendation = match_data.get('fit_recommendation', '')[:20]

                fit.raw_ai_response = match_data
                fit.openai_tokens_used = tokens_per_match
                fit.processing_time_seconds = elapsed
                fit.status = 'done'
                fit.progress = 100
                fit.completed_at = timezone.now()
                fit.error_message = ''
                fit.save()
                updated.append(fit)

                logger.info(
                    f"Batch match: {candidate_profile.name} → "
                    f"{fit.position.title} = {fit.overall_match}%"
                )

            # Requirement-by-requirement analysis for each matched position
            cv_text = candidate_profile.cv_document.extracted_text or ''
            for fit in updated:
                try:
                    analyze_cv_against_position(cv_text, fit.position, fit)
                    logger.info(
                        f"Requirement match: {candidate_profile.name} → "
                        f"{fit.position.title} = {fit.overall_match}% "
                        f"({fit.get_classification()})"
                    )
                except Exception as req_err:
                    logger.error(
                        f"Requirement matching failed for {fit.position.title}: {req_err}"
                    )

            # Section-by-section scoring for each matched position
            for fit in updated:
                try:
                    score_sections(fit)
                    logger.info(
                        f"Section scoring done: {candidate_profile.name} → "
                        f"{fit.position.title}"
                    )
                except Exception as sec_err:
                    logger.error(
                        f"Section scoring failed for {fit.position.title}: {sec_err}"
                    )

            for p in positions:
                self._update_position_stats(p)

            logger.info(
                f"Batch matching: {len(updated)}/{len(positions)} "
                f"positions in {time.time() - start_time:.1f}s ({result['tokens_used']} tokens)"
            )
            return updated

        except Exception as e:
            logger.error(f"Batch matching failed: {e}")
            for p in positions:
                pid = str(p.id)
                if pid in fits:
                    fit = fits[pid]
                    fit.status = 'failed'
                    fit.error_message = str(e)
                    fit.processing_time_seconds = time.time() - start_time
                    fit.save(update_fields=['status', 'error_message', 'processing_time_seconds'])
            return []

    def match_single(self, fit_result_id):
        """Fallback: matching 1 kandydata vs 1 stanowisko."""
        fit = JobFitResult.objects.select_related(
            'candidate', 'position',
        ).get(id=fit_result_id)

        fit.status = 'processing'
        fit.progress = 10
        fit.save(update_fields=['status', 'progress'])

        start_time = time.time()

        try:
            profile = fit.candidate
            position = fit.position

            profile_json = json.dumps({
                'name': profile.name,
                'current_role': profile.current_role,
                'years_of_experience': profile.years_of_experience,
                'seniority_level': profile.seniority_level,
                'skills': profile.skills,
                'skill_levels': profile.skill_levels,
                'education': profile.education,
                'companies': profile.companies[:5],
                'languages': profile.languages,
            }, indent=2)

            position_json = json.dumps({
                'title': position.title,
                'department': position.department,
                'seniority_level': position.seniority_level,
                'required_skills': position.required_skills,
                'optional_skills': position.optional_skills,
                'years_of_experience_required': position.years_of_experience_required,
                'requirements_description': position.requirements_description[:500],
            }, indent=2)

            fit.progress = 40
            fit.save(update_fields=['progress'])

            prompt = POSITION_MATCH_PROMPT.format(
                profile_json=profile_json,
                position_json=position_json,
            )

            result = self.client.chat(SYSTEM_PROMPT, prompt)
            if result['error']:
                raise Exception(f"OpenAI API error: {result['error']}")

            data = self.client.parse_json_response(result['content'])
            if not data:
                raise Exception("Failed to parse matching response")

            fit.progress = 80
            fit.save(update_fields=['progress'])

            scores = data.get('scores', {})
            fit.overall_match = self._clamp(scores.get('overall_match'))
            fit.skill_match = self._clamp(scores.get('skill_match'))
            fit.experience_match = self._clamp(scores.get('experience_match'))
            fit.seniority_match = self._clamp(scores.get('seniority_match'))
            fit.education_match = self._clamp(scores.get('education_match'))

            fit.matching_skills = data.get('matching_skills', [])
            fit.missing_skills = data.get('missing_skills', [])
            fit.fit_recommendation = data.get('fit_recommendation', '')[:20]

            fit.raw_ai_response = data
            fit.openai_tokens_used = result['tokens_used']
            fit.processing_time_seconds = time.time() - start_time
            fit.status = 'done'
            fit.progress = 100
            fit.completed_at = timezone.now()
            fit.error_message = ''
            fit.save()

            # Requirement-by-requirement analysis
            cv_text = profile.cv_document.extracted_text or ''
            try:
                analyze_cv_against_position(cv_text, position, fit)
            except Exception as req_err:
                logger.error(f"Requirement matching failed: {req_err}")

            # Section-by-section scoring
            try:
                score_sections(fit)
            except Exception as sec_err:
                logger.error(f"Section scoring failed: {sec_err}")

            self._update_position_stats(position)
            return fit

        except Exception as e:
            logger.error(f"Position matching failed for {fit_result_id}: {e}")
            fit.status = 'failed'
            fit.error_message = str(e)
            fit.processing_time_seconds = time.time() - start_time
            fit.save(update_fields=['status', 'error_message', 'processing_time_seconds'])
            return fit

    @staticmethod
    def _clamp(value, min_val=0, max_val=100):
        if value is None:
            return None
        try:
            return max(min_val, min(max_val, int(value)))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _update_position_stats(position):
        stats = position.fit_results.filter(status='done').aggregate(
            avg_score=Avg('overall_match'),
            count=Count('id'),
        )
        position.avg_match_score = stats['avg_score']
        position.candidate_count = stats['count']
        position.save(update_fields=['avg_match_score', 'candidate_count'])
