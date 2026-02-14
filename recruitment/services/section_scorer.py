"""recruitment/services/section_scorer.py - Scoring sekcji CV wzgledem stanowiska."""

import json
import logging

from analysis.services.openai_client import OpenAIClient
from analysis.services.text_cleaner import TextCleaner
from cv.models import CVSection
from recruitment.models import SectionScore
from recruitment.services.prompts import SYSTEM_PROMPT, SECTION_SCORE_PROMPT

logger = logging.getLogger(__name__)

# Mapowanie typow sekcji z SectionDetector na typy scoringowe
SECTION_TYPE_MAP = {
    'experience': 'experience',
    'education': 'education',
    'languages': 'languages',
    'skills': 'skills',
    'interests': 'interests',
}

SECTION_DISPLAY_NAMES = {
    'experience': 'Doswiadczenie zawodowe',
    'education': 'Wyksztalcenie',
    'languages': 'Znajomosc jezykow',
    'skills': 'Umiejetnosci',
    'interests': 'Zainteresowania',
}


def score_sections(fit_result):
    """Scoring sekcji CV wzgledem stanowiska.

    1. Pobiera sekcje CV z CVSection
    2. Dla kazdej z 5 sekcji: ocenia AI lub pomija
    3. Zapisuje SectionScore
    4. Zwraca liste SectionScore
    """
    candidate = fit_result.candidate
    position = fit_result.position
    cv_document = candidate.cv_document

    # Pobierz sekcje CV (zapisane podczas uploadu)
    cv_sections = CVSection.objects.filter(document=cv_document)
    sections_by_type = {}
    for cs in cv_sections:
        if cs.section_type in SECTION_TYPE_MAP:
            mapped = SECTION_TYPE_MAP[cs.section_type]
            # Polacz jesli wiele sekcji tego samego typu
            if mapped in sections_by_type:
                sections_by_type[mapped] += '\n' + cs.content
            else:
                sections_by_type[mapped] = cs.content

    # Przygotuj wymagania pozycji (1 raz)
    position_requirements = _build_position_requirements(position)

    # Usun stare wyniki (re-run)
    SectionScore.objects.filter(fit_result=fit_result).delete()

    client = OpenAIClient()
    saved_scores = []

    for section_type, display_name in SECTION_DISPLAY_NAMES.items():
        weight = SectionScore.SECTION_WEIGHTS.get(section_type, 1.0)
        section_text = sections_by_type.get(section_type, '')

        if not section_text:
            # Sekcja nie znaleziona
            ss = SectionScore.objects.create(
                fit_result=fit_result,
                section_name=section_type,
                score=0,
                weight=weight,
                analysis='Sekcja nie zostala znaleziona w CV.',
                section_content='',
            )
            saved_scores.append(ss)
            continue

        cleaned_text = TextCleaner.clean(section_text, max_length=2000)

        if len(cleaned_text) < 300:
            # Zbyt krotka sekcja — nie wysylaj do AI
            ratio = len(cleaned_text) / 300
            score = round(10 + (20 * ratio))  # 10-30%
            ss = SectionScore.objects.create(
                fit_result=fit_result,
                section_name=section_type,
                score=score,
                weight=weight,
                analysis=f'Sekcja zawiera zbyt malo informacji ({len(cleaned_text)} znakow). Automatyczna ocena.',
                section_content=cleaned_text,
            )
            saved_scores.append(ss)
            continue

        # Wywolanie AI
        prompt = SECTION_SCORE_PROMPT.format(
            position_requirements=position_requirements,
            section_name=display_name,
            section_text=cleaned_text,
        )

        response = client.chat(SYSTEM_PROMPT, prompt)

        if response['error']:
            logger.error(f"Section scoring failed for {section_type}: {response['error']}")
            ss = SectionScore.objects.create(
                fit_result=fit_result,
                section_name=section_type,
                score=0,
                weight=weight,
                analysis=f'Blad analizy AI: {response["error"][:200]}',
                section_content=cleaned_text,
            )
            saved_scores.append(ss)
            continue

        parsed = client.parse_json_response(response['content'])
        if not parsed:
            ss = SectionScore.objects.create(
                fit_result=fit_result,
                section_name=section_type,
                score=0,
                weight=weight,
                analysis='Nieprawidlowa odpowiedz AI.',
                section_content=cleaned_text,
            )
            saved_scores.append(ss)
            continue

        score = max(0, min(100, float(parsed.get('score', 0))))
        analysis = parsed.get('analysis', '')

        ss = SectionScore.objects.create(
            fit_result=fit_result,
            section_name=section_type,
            score=round(score, 1),
            weight=weight,
            analysis=analysis,
            section_content=cleaned_text,
        )
        saved_scores.append(ss)

        logger.info(f"Section score: {display_name} = {score:.0f}% (weight {weight}x)")

    # Oblicz wazony final score
    if saved_scores:
        weighted_sum = sum(ss.score * ss.weight for ss in saved_scores)
        max_sum = sum(100 * ss.weight for ss in saved_scores)
        final_score = round((weighted_sum / max_sum) * 100) if max_sum > 0 else 0

        logger.info(
            f"Section final score for {candidate.name} → {position.title}: "
            f"{final_score}%"
        )

    return saved_scores


def _build_position_requirements(position):
    """Buduje tekst wymagan pozycji dla promptu."""
    parts = []

    if position.required_skills:
        parts.append(f"Required skills: {', '.join(position.required_skills)}")
    if position.optional_skills:
        parts.append(f"Optional skills: {', '.join(position.optional_skills)}")
    if position.years_of_experience_required:
        parts.append(f"Experience: {position.years_of_experience_required}+ years")
    if position.seniority_level:
        parts.append(f"Seniority: {position.get_seniority_level_display()}")
    if position.languages_required:
        parts.append(f"Languages: {', '.join(position.languages_required)}")
    if position.requirements_description:
        parts.append(f"Requirements: {position.requirements_description[:500]}")
    if position.responsibilities:
        parts.append(f"Responsibilities: {position.responsibilities[:500]}")

    return '\n'.join(parts) if parts else 'No specific requirements defined.'
