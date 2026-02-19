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
import re
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
        Partial failure: jeśli 1 z 2 promptów się uda → status='partial'.
        """
        analysis = AnalysisResult.objects.select_related('cv_document').get(id=analysis_id)
        analysis.status = 'processing'
        analysis.progress = 10
        analysis.save(update_fields=['status', 'progress'])

        start_time = time.time()
        total_tokens = 0
        is_partial = False

        try:
            # --- Krok 1: Czyszczenie tekstu -> 30% ---
            cv_text = analysis.cv_document.extracted_text
            if not cv_text:
                raise ValueError("CV document has no extracted text")

            cleaned_text = TextCleaner.clean(cv_text, max_length=4000)

            # Short text warning
            metadata = {}
            if len(cleaned_text) < 200:
                metadata['short_text_warning'] = True
                logger.warning(
                    f"Analysis {analysis_id}: short CV text ({len(cleaned_text)} chars)"
                )

            analysis.progress = 30
            analysis.save(update_fields=['progress'])

            # --- Krok 2: Prompt 1 - Ekstrakcja + problemy -> 60% ---
            extraction_data = None
            extracted = {}

            try:
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

            except Exception as ext_err:
                logger.error(f"Analysis {analysis_id} extraction failed: {ext_err}")
                is_partial = True
                # Regex fallback for basic info
                fallback = self._regex_fallback(cv_text)
                extracted = {'regex_fallback': fallback}

            analysis.progress = 60
            analysis.save(update_fields=['progress', 'sections_detected'])

            # --- Krok 3: Prompt 2 - Jakosciowa analiza sekcji -> 90% ---
            analysis_data = None

            try:
                problems_summary = "None"
                if extraction_data:
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

            except Exception as sec_err:
                logger.error(f"Analysis {analysis_id} section analysis failed: {sec_err}")
                is_partial = True

            analysis.progress = 90
            analysis.save(update_fields=['progress'])

            # --- Krok 4: Zapis wynikow -> 100% ---
            if analysis_data:
                analysis.summary = analysis_data.get('summary', '')
                self._save_section_analyses(analysis, analysis_data.get('section_analyses', []))
                self._save_recommendations(analysis, analysis_data.get('recommendations', []))
                self._save_skill_gaps(analysis, analysis_data.get('skill_gaps', []))

            raw_response = {}
            if extraction_data:
                raw_response['extraction'] = extraction_data
            if analysis_data:
                raw_response['section_analysis'] = analysis_data
            if metadata:
                raw_response['metadata'] = metadata

            analysis.raw_ai_response = raw_response
            analysis.openai_tokens_used = total_tokens
            analysis.processing_time_seconds = time.time() - start_time
            analysis.status = 'partial' if is_partial else 'done'
            analysis.progress = 100
            analysis.completed_at = timezone.now()
            analysis.error_message = 'Partial results — some AI prompts failed.' if is_partial else ''
            analysis.save()

            if analysis.user and not is_partial:
                analysis.user.use_analysis()

            logger.info(
                f"Analysis {analysis_id} {'partial' if is_partial else 'completed'} in "
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

        # Cache hit — don't increment usage counter
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

    @staticmethod
    def _regex_fallback(text):
        """Fallback: wyciąga email, phone, name z surowego tekstu CV przy pomocy regex."""
        result = {'email': '', 'phone': '', 'name': ''}

        # Email
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if email_match:
            result['email'] = email_match.group()

        # Phone (international + local formats)
        phone_match = re.search(r'[\+]?[\d\s\-\(\)]{7,15}', text)
        if phone_match:
            candidate = phone_match.group().strip()
            digits = re.sub(r'\D', '', candidate)
            if 7 <= len(digits) <= 15:
                result['phone'] = candidate

        # Name (first non-empty line heuristic)
        for line in text.split('\n'):
            line = line.strip()
            if line and len(line) < 60 and not re.search(r'[@\d]', line):
                result['name'] = line
                break

        return result
