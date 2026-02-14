"""recruitment/services/requirement_matcher.py - Dopasowanie requirement-by-requirement CV do pozycji."""

import json
import logging
import re
import time

from django.utils import timezone

from analysis.services.openai_client import OpenAIClient
from analysis.services.text_cleaner import TextCleaner
from recruitment.models import RequirementMatch
from recruitment.services.prompts import SYSTEM_PROMPT, REQUIREMENT_MATCH_PROMPT

logger = logging.getLogger(__name__)


def split_text_to_items(text):
    """Rozbija tekst (responsibilities/requirements) na atomiczne pozycje."""
    if not text:
        return []
    lines = re.split(r'[\n;]+', text)
    items = []
    for line in lines:
        line = re.sub(r'^[\s\-\*\•\d\.]+', '', line).strip()
        if line and len(line) > 3:
            items.append(line)
    return items


def extract_requirements(position):
    """Wyciaga atomiczne wymagania z JobPosition z typem i waga."""
    requirements = []

    for skill in (position.required_skills or []):
        requirements.append({
            'text': skill,
            'type': 'skill_required',
            'weight': RequirementMatch.WEIGHTS['skill_required'],
        })

    for skill in (position.optional_skills or []):
        requirements.append({
            'text': skill,
            'type': 'skill_optional',
            'weight': RequirementMatch.WEIGHTS['skill_optional'],
        })

    if position.responsibilities:
        for item in split_text_to_items(position.responsibilities):
            requirements.append({
                'text': item,
                'type': 'responsibility',
                'weight': RequirementMatch.WEIGHTS['responsibility'],
            })

    if position.requirements_description:
        for item in split_text_to_items(position.requirements_description):
            requirements.append({
                'text': item,
                'type': 'skill_required',
                'weight': RequirementMatch.WEIGHTS['skill_required'],
            })

    if position.years_of_experience_required and position.years_of_experience_required > 0:
        requirements.append({
            'text': f'{position.years_of_experience_required}+ years of experience',
            'type': 'experience',
            'weight': RequirementMatch.WEIGHTS['experience'],
        })

    for lang in (position.languages_required or []):
        requirements.append({
            'text': lang,
            'type': 'language',
            'weight': RequirementMatch.WEIGHTS['language'],
        })

    return requirements


def analyze_cv_against_position(cv_text, position, fit_result):
    """Glowna funkcja: analizuje CV wzgledem pozycji requirement-by-requirement.

    1. Wyciaga wymagania z pozycji
    2. Wysyla 1 request do OpenAI z wszystkimi wymaganiami + CV
    3. Zapisuje RequirementMatch dla kazdego wymagania
    4. Oblicza wazony overall_match
    5. Ustawia klasyfikacje (Excellent/Strong/Moderate/Weak/Poor)
    """
    start_time = time.time()

    requirements = extract_requirements(position)
    if not requirements:
        fit_result.overall_match = 0
        fit_result.fit_recommendation = 'poor'
        fit_result.status = 'done'
        fit_result.progress = 100
        fit_result.completed_at = timezone.now()
        fit_result.save()
        return

    # Czyszczenie CV
    cleaned_cv = TextCleaner.clean(cv_text, max_length=4000)
    if not cleaned_cv:
        fit_result.overall_match = 0
        fit_result.fit_recommendation = 'poor'
        fit_result.status = 'done'
        fit_result.progress = 100
        fit_result.error_message = 'No CV text to analyze.'
        fit_result.completed_at = timezone.now()
        fit_result.save()
        return

    # Update progress
    fit_result.progress = 20
    fit_result.save(update_fields=['progress'])

    # Przygotuj liste wymagan dla promptu
    req_list = [r['text'] for r in requirements]
    requirements_json = json.dumps(req_list, ensure_ascii=False)

    prompt = REQUIREMENT_MATCH_PROMPT.format(
        requirements_json=requirements_json,
        cv_text=cleaned_cv,
    )

    # 1 request OpenAI = wszystkie wymagania
    client = OpenAIClient()
    response = client.chat(SYSTEM_PROMPT, prompt)

    fit_result.progress = 60
    fit_result.save(update_fields=['progress'])

    if response['error']:
        fit_result.status = 'failed'
        fit_result.error_message = response['error']
        fit_result.progress = 100
        fit_result.completed_at = timezone.now()
        fit_result.save()
        return

    fit_result.openai_tokens_used = response.get('tokens_used', 0)

    parsed = client.parse_json_response(response['content'])
    if not parsed or 'requirements' not in parsed:
        fit_result.status = 'failed'
        fit_result.error_message = 'Invalid AI response format.'
        fit_result.progress = 100
        fit_result.completed_at = timezone.now()
        fit_result.save()
        return

    fit_result.raw_ai_response = parsed
    fit_result.progress = 80
    fit_result.save(update_fields=['progress', 'raw_ai_response', 'openai_tokens_used'])

    # Usun stare RequirementMatch dla tego fit_result (re-run)
    RequirementMatch.objects.filter(fit_result=fit_result).delete()

    # Parsowanie wynikow i zapis RequirementMatch
    ai_results = parsed['requirements']
    saved_matches = []

    for i, req in enumerate(requirements):
        # Znajdz odpowiadajacy wynik AI (po indeksie lub tekscie)
        ai_match = ai_results[i] if i < len(ai_results) else None

        match_pct = 0
        explanation = ''

        if ai_match:
            match_pct = _clamp(ai_match.get('match_percentage', 0))
            explanation = ai_match.get('explanation', '')

        rm = RequirementMatch.objects.create(
            fit_result=fit_result,
            requirement_text=req['text'],
            requirement_type=req['type'],
            match_percentage=match_pct,
            explanation=explanation,
            weight=req['weight'],
        )
        saved_matches.append(rm)

    # Oblicz wazony overall_match
    weighted_score = sum(rm.match_percentage * rm.weight for rm in saved_matches)
    max_possible = sum(100 * rm.weight for rm in saved_matches)
    overall_match = round((weighted_score / max_possible) * 100) if max_possible > 0 else 0

    # Oblicz score'y per typ (skill, experience, etc.)
    skill_matches = [rm for rm in saved_matches if rm.requirement_type in ('skill_required', 'skill_optional')]
    exp_matches = [rm for rm in saved_matches if rm.requirement_type == 'experience']
    lang_matches = [rm for rm in saved_matches if rm.requirement_type == 'language']
    resp_matches = [rm for rm in saved_matches if rm.requirement_type == 'responsibility']

    fit_result.overall_match = _clamp(overall_match)
    fit_result.skill_match = _avg_pct(skill_matches) if skill_matches else None
    fit_result.experience_match = _avg_pct(exp_matches) if exp_matches else None
    fit_result.education_match = _avg_pct(lang_matches) if lang_matches else None
    fit_result.seniority_match = _avg_pct(resp_matches) if resp_matches else None

    # Matching/missing skills
    fit_result.matching_skills = [
        rm.requirement_text for rm in saved_matches
        if rm.requirement_type in ('skill_required', 'skill_optional') and rm.match_percentage >= 60
    ]
    fit_result.missing_skills = [
        rm.requirement_text for rm in saved_matches
        if rm.requirement_type in ('skill_required', 'skill_optional') and rm.match_percentage < 60
    ]

    # Klasyfikacja
    fit_result.fit_recommendation = _get_recommendation(overall_match)

    # Finalizacja
    elapsed = time.time() - start_time
    fit_result.processing_time_seconds = round(elapsed, 2)
    fit_result.status = 'done'
    fit_result.progress = 100
    fit_result.completed_at = timezone.now()
    fit_result.save()

    # Update position stats
    _update_position_stats(fit_result.position)


def _clamp(value, min_val=0, max_val=100):
    """Ogranicza wartosc do zakresu."""
    try:
        return max(min_val, min(max_val, int(float(value))))
    except (TypeError, ValueError):
        return 0


def _avg_pct(matches):
    """Srednia procentowa z listy RequirementMatch."""
    if not matches:
        return None
    return _clamp(round(sum(rm.match_percentage for rm in matches) / len(matches)))


def _get_recommendation(score):
    """Klasyfikacja dopasowania."""
    if score >= 90:
        return 'excellent'
    if score >= 75:
        return 'strong_fit'
    if score >= 60:
        return 'good_fit'
    if score >= 40:
        return 'moderate_fit'
    if score >= 20:
        return 'weak_fit'
    return 'poor'


def _update_position_stats(position):
    """Aktualizuje zagregowane statystyki pozycji."""
    from django.db.models import Avg, Count
    from recruitment.models import JobFitResult

    stats = JobFitResult.objects.filter(
        position=position, status='done',
    ).aggregate(
        avg_score=Avg('overall_match'),
        total=Count('id'),
    )

    position.avg_match_score = round(stats['avg_score'], 1) if stats['avg_score'] else None
    position.candidate_count = stats['total']
    position.save(update_fields=['avg_match_score', 'candidate_count'])
