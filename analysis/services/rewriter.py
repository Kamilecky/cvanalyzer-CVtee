"""analysis/services/rewriter.py - Serwis przepisywania sekcji CV przez AI."""

import logging
from analysis.models import AnalysisResult, RewrittenSection
from .openai_client import OpenAIClient
from .prompts import SYSTEM_PROMPT, REWRITE_PROMPT

logger = logging.getLogger(__name__)


class CVRewriter:
    """Przepisuje sekcję CV używając OpenAI GPT."""

    def __init__(self):
        self.client = OpenAIClient()

    def rewrite_section(self, analysis_id, section_type, original_text):
        """Przepisuje jedną sekcję CV.

        Args:
            analysis_id: UUID AnalysisResult
            section_type: typ sekcji (experience, education, etc.)
            original_text: oryginalny tekst sekcji

        Returns:
            RewrittenSection lub None w przypadku błędu
        """
        analysis = AnalysisResult.objects.get(id=analysis_id)

        problems = analysis.problems.filter(section__icontains=section_type)
        problems_context = "\n".join(
            f"- [{p.severity}] {p.title}: {p.description}"
            for p in problems
        ) or "No specific problems detected for this section."

        prompt = REWRITE_PROMPT.format(
            section_type=section_type,
            original_text=original_text[:4000],
            problems_context=problems_context,
        )

        result = self.client.chat(SYSTEM_PROMPT, prompt)
        if result['error']:
            logger.error(f"Rewrite failed for analysis {analysis_id}: {result['error']}")
            return None

        data = self.client.parse_json_response(result['content'])
        if not data:
            return None

        rewrite = RewrittenSection.objects.create(
            analysis=analysis,
            section_type=section_type,
            original_text=original_text,
            rewritten_text=data.get('rewritten_text', ''),
            improvement_notes=data.get('improvement_notes', ''),
        )

        analysis.openai_tokens_used += result['tokens_used']
        analysis.save(update_fields=['openai_tokens_used'])

        return rewrite
