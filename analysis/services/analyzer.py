"""analysis/services/analyzer.py - Orkiestrator pelnej analizy CV.

Zoptymalizowany pipeline (threading, bez Celery):
1. Parsowanie + czyszczenie tekstu -> progress 10%
2. AI Prompt 1: Ekstrakcja danych + problemy -> progress 30% -> 60%
3. AI Prompt 2: Jakosciowa analiza sekcji + rekomendacje -> progress 60% -> 90%
4. Zapis wynikow -> progress 100%

Docelowy czas: ~4-10s dla 1-stronicowego CV.
"""

import hashlib
import json
import logging
import time
from django.utils import timezone

from analysis.models import (
    AnalysisResult, Problem, Recommendation, SkillGap, SectionAnalysis,
)
from .openai_client import OpenAIClient
from .prompts import SYSTEM_PROMPT, EXTRACTION_PROMPT, SECTION_ANALYSIS_PROMPT
from .text_cleaner import TextCleaner

logger = logging.getLogger(__name__)


class CVAnalyzer:
    """Orkiestrator analizy CV - 2-promptowy pipeline z threading."""

    def __init__(self):
        self.client = OpenAIClient()

    def run_analysis(self, analysis_id):
        """Uruchamia pelna analize CV z progress tracking.

        Progress: 10% -> 30% -> 60% -> 90% -> 100%
        """
        analysis = AnalysisResult.objects.select_related('cv_document').get(id=analysis_id)
        analysis.status = 'processing'
        analysis.progress = 10
        analysis.save(update_fields=['status', 'progress'])

        start_time = time.time()
        total_tokens = 0

        try:
            # --- Krok 1: Czyszczenie tekstu -> 30% ---
            cv_text = analysis.cv_document.extracted_text
            if not cv_text:
                raise ValueError("CV document has no extracted text")

            cleaned_text = TextCleaner.clean(cv_text, max_length=4000)

            analysis.progress = 30
            analysis.save(update_fields=['progress'])

            # --- Krok 2: Prompt 1 - Ekstrakcja + problemy -> 60% ---
            extraction_prompt = EXTRACTION_PROMPT.format(cv_text=cleaned_text)

            extraction_result = self.client.chat(SYSTEM_PROMPT, extraction_prompt)
            if extraction_result['error']:
                raise Exception(f"Extraction API error: {extraction_result['error']}")

            extraction_data = self.client.parse_json_response(extraction_result['content'])
            if not extraction_data:
                raise Exception("Failed to parse extraction response")

            total_tokens += extraction_result['tokens_used']

            self._save_problems(analysis, extraction_data.get('problems', []))

            extracted = extraction_data.get('extracted', {})
            analysis.sections_detected = extracted.get('sections_detected', [])
            analysis.progress = 60
            analysis.save(update_fields=['progress', 'sections_detected'])

            # --- Krok 3: Prompt 2 - Jakosciowa analiza sekcji -> 90% ---
            problems_summary = ", ".join(
                p.get('title', '') for p in extraction_data.get('problems', [])
            ) or "None"

            sections_content = self._build_sections_content(analysis.cv_document)
            sections_list = ", ".join(analysis.sections_detected) if analysis.sections_detected else "None detected"

            analysis_prompt = SECTION_ANALYSIS_PROMPT.format(
                extracted_json=json.dumps(extracted, indent=2),
                sections_list=sections_list,
                problems_summary=problems_summary,
                sections_content=sections_content,
            )

            analysis_result = self.client.chat(SYSTEM_PROMPT, analysis_prompt)
            if analysis_result['error']:
                raise Exception(f"Section analysis API error: {analysis_result['error']}")

            analysis_data = self.client.parse_json_response(analysis_result['content'])
            if not analysis_data:
                raise Exception("Failed to parse section analysis response")

            total_tokens += analysis_result['tokens_used']

            analysis.progress = 90
            analysis.save(update_fields=['progress'])

            # --- Krok 4: Zapis wynikow -> 100% ---
            analysis.summary = analysis_data.get('summary', '')
            self._save_section_analyses(analysis, analysis_data.get('section_analyses', []))
            self._save_recommendations(analysis, analysis_data.get('recommendations', []))
            self._save_skill_gaps(analysis, analysis_data.get('skill_gaps', []))

            analysis.raw_ai_response = {
                'extraction': extraction_data,
                'section_analysis': analysis_data,
            }
            analysis.openai_tokens_used = total_tokens
            analysis.processing_time_seconds = time.time() - start_time
            analysis.status = 'done'
            analysis.progress = 100
            analysis.completed_at = timezone.now()
            analysis.error_message = ''
            analysis.save()

            if analysis.user:
                analysis.user.use_analysis()

            logger.info(
                f"Analysis {analysis_id} completed in "
                f"{analysis.processing_time_seconds:.1f}s, "
                f"{total_tokens} tokens"
            )
            return analysis

        except Exception as e:
            logger.error(f"Analysis {analysis_id} failed: {e}")
            analysis.status = 'failed'
            analysis.error_message = str(e)
            analysis.processing_time_seconds = time.time() - start_time
            analysis.save(update_fields=[
                'status', 'error_message', 'processing_time_seconds'
            ])
            return analysis

    # --- Cache: sprawdzenie hash pliku ---

    @staticmethod
    def check_cache(cv_document):
        """Sprawdza czy istnieje gotowa analiza dla identycznego CV (hash)."""
        if not cv_document.file_hash:
            return None

        from cv.models import CVDocument
        cached_docs = CVDocument.objects.filter(
            file_hash=cv_document.file_hash,
            is_active=True,
        ).exclude(id=cv_document.id)

        for doc in cached_docs:
            cached_analysis = doc.analyses.filter(status='done').order_by('-created_at').first()
            if cached_analysis:
                return cached_analysis

        return None

    @staticmethod
    def clone_analysis(source_analysis, target_cv, user):
        """Klonuje wyniki analizy z cache do nowego CV."""
        new_analysis = AnalysisResult.objects.create(
            user=user,
            cv_document=target_cv,
            status='done',
            progress=100,
            summary=source_analysis.summary,
            sections_detected=source_analysis.sections_detected,
            raw_ai_response=source_analysis.raw_ai_response,
            processing_time_seconds=0,
            openai_tokens_used=0,
            completed_at=timezone.now(),
        )

        for p in source_analysis.problems.all():
            Problem.objects.create(
                analysis=new_analysis,
                category=p.category,
                severity=p.severity,
                title=p.title,
                description=p.description,
                section=p.section,
                affected_text=p.affected_text,
            )

        for sa in source_analysis.section_analyses.all():
            SectionAnalysis.objects.create(
                analysis=new_analysis,
                section=sa.section,
                status=sa.status,
                analysis_text=sa.analysis_text,
                suggestions=sa.suggestions,
            )

        for r in source_analysis.recommendations.all():
            Recommendation.objects.create(
                analysis=new_analysis,
                recommendation_type=r.recommendation_type,
                priority=r.priority,
                title=r.title,
                description=r.description,
                section=r.section,
                suggested_text=r.suggested_text,
            )

        for sg in source_analysis.skill_gaps.all():
            SkillGap.objects.create(
                analysis=new_analysis,
                skill_name=sg.skill_name,
                current_level=sg.current_level,
                recommended_level=sg.recommended_level,
                importance=sg.importance,
                learning_resources=sg.learning_resources,
            )

        if user:
            user.use_analysis()

        return new_analysis

    @staticmethod
    def compute_file_hash(file_obj):
        """Oblicza MD5 hash pliku."""
        md5 = hashlib.md5()
        for chunk in file_obj.chunks():
            md5.update(chunk)
        file_obj.seek(0)
        return md5.hexdigest()

    # --- Helpery zapisu wynikow ---

    def _build_sections_content(self, cv_document):
        """Buduje tekst sekcji CV z CVSection."""
        from cv.models import CVSection
        sections = CVSection.objects.filter(document=cv_document).order_by('order')

        if not sections.exists():
            return "No sections detected."

        parts = []
        for s in sections:
            content = TextCleaner.clean(s.content, max_length=800)
            parts.append(f"=== {s.get_section_type_display()} ===\n{content}")

        return "\n\n".join(parts)

    def _save_section_analyses(self, analysis, section_analyses):
        valid_statuses = {'present', 'missing', 'weak'}

        for sa in section_analyses:
            status = sa.get('status', 'present')
            if status not in valid_statuses:
                status = 'present'

            SectionAnalysis.objects.create(
                analysis=analysis,
                section=sa.get('section', '')[:50],
                status=status,
                analysis_text=sa.get('analysis', ''),
                suggestions=sa.get('suggestions', []),
            )

    def _save_problems(self, analysis, problems):
        valid_categories = dict(Problem.CATEGORY_CHOICES).keys()
        valid_severities = dict(Problem.SEVERITY_CHOICES).keys()

        for p in problems:
            category = p.get('category', 'other')
            if category not in valid_categories:
                category = 'other'
            severity = p.get('severity', 'warning')
            if severity not in valid_severities:
                severity = 'warning'

            Problem.objects.create(
                analysis=analysis,
                category=category,
                severity=severity,
                title=p.get('title', '')[:255],
                description=p.get('description', ''),
                section=p.get('section', '')[:50],
                affected_text=p.get('affected_text', ''),
            )

    def _save_recommendations(self, analysis, recommendations):
        valid_types = dict(Recommendation.TYPE_CHOICES).keys()
        valid_priorities = dict(Recommendation.PRIORITY_CHOICES).keys()

        for r in recommendations:
            rec_type = r.get('type', 'rewrite')
            if rec_type not in valid_types:
                rec_type = 'rewrite'
            priority = r.get('priority', 'medium')
            if priority not in valid_priorities:
                priority = 'medium'

            Recommendation.objects.create(
                analysis=analysis,
                recommendation_type=rec_type,
                priority=priority,
                title=r.get('title', '')[:255],
                description=r.get('description', ''),
                section=r.get('section', '')[:50],
                suggested_text=r.get('suggested_text', ''),
            )

    def _save_skill_gaps(self, analysis, skill_gaps):
        for sg in skill_gaps:
            SkillGap.objects.create(
                analysis=analysis,
                skill_name=sg.get('skill_name', '')[:255],
                current_level=sg.get('current_level', '')[:50],
                recommended_level=sg.get('recommended_level', '')[:50],
                importance=sg.get('importance', 'medium')[:20],
                learning_resources=sg.get('learning_resources', ''),
            )
