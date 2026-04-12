"""recruitment/services/intelligence_analyzer.py

Generates the Candidate Intelligence Layer (Premium/Enterprise only).
Single GPT-4o-mini call: profile JSON → skill_fit, learnability,
career_trajectory, behavioral_signals, risk_flags, recommendation.
"""

import json
import logging

from analysis.services.openai_client import OpenAIClient
from .prompts import SYSTEM_PROMPT, CANDIDATE_INTELLIGENCE_PROMPT

logger = logging.getLogger(__name__)

_VALID_TRAJECTORY = {'ascending', 'lateral', 'stagnant', 'early'}
_VALID_CONFIDENCE = {'high', 'medium', 'low'}
_VALID_RECOMMENDATION = {'invite', 'consider', 'reject'}
_VALID_SIGNAL_TYPE = {'positive', 'negative', 'neutral'}
_VALID_SEVERITY = {'high', 'medium', 'low'}


class IntelligenceAnalyzer:
    """Generates CandidateIntelligence from a CandidateProfile."""

    def __init__(self):
        self.client = OpenAIClient()

    def analyse(self, candidate_profile):
        """Run intelligence analysis and persist results.

        Args:
            candidate_profile: CandidateProfile instance (status must be 'done').

        Returns:
            CandidateIntelligence instance (status 'done' or 'failed').
        """
        from recruitment.models import CandidateIntelligence

        intel, _ = CandidateIntelligence.objects.get_or_create(profile=candidate_profile)
        intel.status = 'pending'
        intel.save(update_fields=['status'])

        try:
            profile_data = {
                'name': candidate_profile.name,
                'current_role': candidate_profile.current_role,
                'years_of_experience': candidate_profile.years_of_experience,
                'seniority_level': candidate_profile.seniority_level,
                'skills': candidate_profile.skills,
                'skill_levels': candidate_profile.skill_levels,
                'education': candidate_profile.education,
                'companies': candidate_profile.companies,
                'languages': candidate_profile.languages,
                'certifications': candidate_profile.certifications,
                'red_flags': candidate_profile.red_flags,
                'hr_summary': candidate_profile.hr_summary,
            }

            prompt = CANDIDATE_INTELLIGENCE_PROMPT.format(
                profile_json=json.dumps(profile_data, ensure_ascii=False),
            )

            result = self.client.chat(SYSTEM_PROMPT, prompt)
            if result['error']:
                raise Exception(f"OpenAI error: {result['error']}")

            data = self.client.parse_json_response(result['content'])
            if not data:
                raise Exception("Empty or unparseable AI response")

            self._apply(intel, data)
            intel.status = 'done'
            intel.error_message = ''
            intel.save()

            logger.info(f"Intelligence done for {candidate_profile.name}: {intel.recommendation}")
            return intel

        except Exception as e:
            logger.error(f"Intelligence analysis failed for {candidate_profile.name}: {e}")
            intel.status = 'failed'
            intel.error_message = str(e)
            intel.save(update_fields=['status', 'error_message'])
            return intel

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply(self, intel, data):
        """Map validated AI response fields onto the model instance."""
        intel.skill_fit = self._validate_skill_fit(data.get('skill_fit', {}))
        intel.learnability = self._validate_learnability(data.get('learnability', {}))
        intel.career_trajectory = self._validate_trajectory(data.get('career_trajectory', {}))
        intel.behavioral_signals = self._validate_signals(data.get('behavioral_signals', []))
        intel.risk_flags = self._validate_risk_flags(data.get('risk_flags', []))
        intel.confidence = data.get('confidence', 'medium') if data.get('confidence') in _VALID_CONFIDENCE else 'medium'
        intel.recommendation = data.get('recommendation', 'consider') if data.get('recommendation') in _VALID_RECOMMENDATION else 'consider'
        intel.recommendation_reason = str(data.get('recommendation_reason', ''))[:500]

    @staticmethod
    def _validate_skill_fit(sf):
        score = sf.get('score', 0)
        return {
            'score': max(0, min(100, int(score))) if isinstance(score, (int, float)) else 0,
            'strong_skills': [str(s) for s in sf.get('strong_skills', [])[:5]],
            'weak_skills': [str(s) for s in sf.get('weak_skills', [])[:3]],
            'summary': str(sf.get('summary', ''))[:200],
        }

    @staticmethod
    def _validate_learnability(lb):
        score = lb.get('score', 0)
        return {
            'score': max(0, min(100, int(score))) if isinstance(score, (int, float)) else 0,
            'signals': [str(s) for s in lb.get('signals', [])[:4]],
        }

    @staticmethod
    def _validate_trajectory(ct):
        t = ct.get('type', 'early')
        return {
            'type': t if t in _VALID_TRAJECTORY else 'early',
            'summary': str(ct.get('summary', ''))[:200],
        }

    @staticmethod
    def _validate_signals(signals):
        out = []
        for s in signals[:5]:
            if not isinstance(s, dict):
                continue
            out.append({
                'signal': str(s.get('signal', ''))[:150],
                'type': s.get('type', 'neutral') if s.get('type') in _VALID_SIGNAL_TYPE else 'neutral',
            })
        return out

    @staticmethod
    def _validate_risk_flags(flags):
        out = []
        for f in flags[:3]:
            if not isinstance(f, dict):
                continue
            out.append({
                'flag': str(f.get('flag', ''))[:150],
                'severity': f.get('severity', 'low') if f.get('severity') in _VALID_SEVERITY else 'low',
            })
        return out
