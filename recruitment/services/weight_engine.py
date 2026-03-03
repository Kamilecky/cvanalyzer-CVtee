"""recruitment/services/weight_engine.py - Silnik rankingu kandydatów oparty na wagach kryteriów HR.

Logika:
- Każde kryterium (experience, education, hard_skills, soft_skills, certifications, languages)
  ma wagę 0-10 ustawianą przez rekrutera.
- Wynik ważony = suma(waga_i * wynik_i) / suma(wag)
- Wyniki cząstkowe pobierane z: JobFitResult (direct fields), SectionScore (AI), CandidateProfile (derived).
- Sugestie ('Warto podkreślić') generowane per kandydat na podstawie profilu i wyników dopasowania.
"""

import logging

logger = logging.getLogger(__name__)

# Keywords identifying prestige companies
_PRESTIGE_KEYWORDS = frozenset([
    'google', 'microsoft', 'amazon', 'apple', 'meta', 'netflix', 'uber', 'airbnb',
    'tesla', 'nvidia', 'ibm', 'oracle', 'sap', 'salesforce', 'accenture', 'deloitte',
    'mckinsey', 'bcg', 'goldman', 'jp morgan', 'pwc', 'kpmg', 'bain', 'ey', 'booz',
    'spotify', 'twitter', 'linkedin', 'stripe', 'twilio', 'shopify', 'atlassian',
])

# Soft-skill related tag keywords
_SOFT_KEYWORDS = frozenset([
    'leadership', 'teamwork', 'communication', 'mentoring', 'coaching',
    'adaptability', 'creativity', 'empathy', 'negotiation', 'presentation',
    'zarządzanie', 'komunikacja', 'przywódstwo', 'motywacja',
])

# Default weight configuration
DEFAULT_WEIGHTS = {
    'experience': 5.0,
    'education': 3.0,
    'certifications': 2.0,
    'hard_skills': 5.0,
    'soft_skills': 2.0,
    'languages': 3.0,
}

CRITERIA_LABELS = {
    'experience': 'Work Experience',
    'education': 'Education',
    'certifications': 'Certifications',
    'hard_skills': 'Hard Skills',
    'soft_skills': 'Soft Skills',
    'languages': 'Languages',
}


def _clamp(value, lo=0.0, hi=10.0):
    return max(lo, min(hi, float(value)))


def weights_from_dict(raw: dict) -> dict:
    """Parse and clamp weights dict from request data."""
    return {key: _clamp(raw.get(key, DEFAULT_WEIGHTS[key])) for key in DEFAULT_WEIGHTS}


def _cert_score(certifications) -> float:
    """Convert number of certifications to 0-100 score."""
    n = len(certifications) if certifications else 0
    if n == 0:
        return 10.0
    if n == 1:
        return 50.0
    if n == 2:
        return 70.0
    if n == 3:
        return 85.0
    return 100.0


def _soft_skill_score(profile, fit) -> float:
    """Derive soft-skill score from seniority_match and tags."""
    if fit.seniority_match is not None:
        return float(fit.seniority_match)
    tags = [t.lower() for t in (profile.tags or [])]
    soft_count = sum(1 for t in tags if any(kw in t for kw in _SOFT_KEYWORDS))
    return min(soft_count * 20.0, 90.0) or 40.0


def compute_candidate_weighted_score(fit, profile, weights: dict) -> float:
    """Oblicza wyważony wynik kandydata.

    Args:
        fit: JobFitResult instance (with prefetched section_scores)
        profile: CandidateProfile instance
        weights: dict with keys matching DEFAULT_WEIGHTS

    Returns:
        Weighted score 0-100 (float, 1 decimal)
    """
    # Build section score map
    section_map = {ss.section_name: float(ss.score) for ss in fit.section_scores.all()}

    experience_score = float(fit.experience_match or section_map.get('experience', 0) or 0)
    education_score = float(fit.education_match or section_map.get('education', 0) or 0)
    hard_skill_score = float(fit.skill_match or section_map.get('skills', 0) or 0)
    language_score = float(section_map.get('languages', 0) or 0)
    cert_score = _cert_score(profile.certifications)
    soft_score = _soft_skill_score(profile, fit)

    total_weight = sum(weights.values())
    if total_weight == 0:
        return float(fit.overall_match or 0)

    weighted_sum = (
        weights['experience'] * experience_score
        + weights['education'] * education_score
        + weights['certifications'] * cert_score
        + weights['hard_skills'] * hard_skill_score
        + weights['soft_skills'] * soft_score
        + weights['languages'] * language_score
    )
    return round(weighted_sum / total_weight, 1)


def get_candidate_suggestions(profile, fit) -> list:
    """Returns list of highlight badge dicts for a candidate.

    Each dict: {type, label, icon, color}
    """
    suggestions = []

    # Prestige company
    company_names = [str(c).lower() for c in (profile.companies or [])]
    if any(kw in name for name in company_names for kw in _PRESTIGE_KEYWORDS):
        suggestions.append({
            'type': 'prestige',
            'label': 'Prestige company',
            'icon': 'bi-award-fill',
            'color': 'success',
        })

    # Certifications
    cert_count = len(profile.certifications or [])
    if cert_count >= 2:
        suggestions.append({
            'type': 'certs',
            'label': f'{cert_count} certifications',
            'icon': 'bi-patch-check-fill',
            'color': 'primary',
        })
    elif cert_count == 1:
        suggestions.append({
            'type': 'certs',
            'label': '1 certification',
            'icon': 'bi-patch-check',
            'color': 'info',
        })

    # Multilingual
    lang_count = len(profile.languages or [])
    if lang_count >= 3:
        suggestions.append({
            'type': 'languages',
            'label': f'{lang_count} languages',
            'icon': 'bi-translate',
            'color': 'warning',
        })

    # Strong skill match
    match_count = len(fit.matching_skills or [])
    if match_count >= 5:
        suggestions.append({
            'type': 'skills',
            'label': f'{match_count} matching skills',
            'icon': 'bi-lightning-charge-fill',
            'color': 'success',
        })

    # Red flags warning
    flag_count = len(profile.red_flags or [])
    if flag_count:
        suggestions.append({
            'type': 'red_flag',
            'label': f'{flag_count} red flag{"s" if flag_count > 1 else ""}',
            'icon': 'bi-exclamation-triangle-fill',
            'color': 'danger',
        })

    return suggestions


def compute_ranking(position, weights: dict, user) -> list:
    """Oblicza pełny ranking kandydatów dla stanowiska.

    Args:
        position: JobPosition instance
        weights: dict {criterion: weight_value}
        user: User instance

    Returns:
        List of dicts sorted by weighted_score descending, each with rank 1-N.
    """
    from recruitment.models import JobFitResult

    fits = (
        JobFitResult.objects
        .filter(position=position, user=user, status__in=['done', 'partial'])
        .select_related('candidate')
        .prefetch_related('section_scores')
    )

    results = []
    for fit in fits:
        profile = fit.candidate
        weighted_score = compute_candidate_weighted_score(fit, profile, weights)
        suggestions = get_candidate_suggestions(profile, fit)

        results.append({
            'fit_id': str(fit.id),
            'profile_id': str(profile.id),
            'name': profile.name or f'Candidate {str(profile.id)[:8]}',
            'current_role': profile.current_role or '—',
            'seniority_level': profile.seniority_level or '',
            'original_match': fit.overall_match or 0,
            'weighted_score': weighted_score,
            'experience_score': fit.experience_match or 0,
            'skill_score': fit.skill_match or 0,
            'education_score': fit.education_match or 0,
            'seniority_score': fit.seniority_match or 0,
            'cert_score': round(_cert_score(profile.certifications)),
            'lang_score': round(next(
                (ss.score for ss in fit.section_scores.all() if ss.section_name == 'languages'), 0
            )),
            'fit_recommendation': fit.fit_recommendation,
            'suggestions': suggestions,
        })

    results.sort(key=lambda x: x['weighted_score'], reverse=True)
    for i, r in enumerate(results):
        r['rank'] = i + 1

    return results


def get_panel_suggestions(position, results: list) -> list:
    """Generates aggregate suggestions for the weight panel.

    Analyzes all candidate results and suggests which criteria to emphasize.

    Returns:
        List of {criterion, label, message, icon} dicts.
    """
    if not results:
        return []

    total = len(results)
    suggestions = []

    cert_count = sum(1 for r in results if r['cert_score'] > 10)
    if cert_count >= max(2, total // 3):
        suggestions.append({
            'criterion': 'certifications',
            'label': CRITERIA_LABELS['certifications'],
            'message': f'{cert_count}/{total} candidates have certifications — consider raising this weight.',
            'icon': 'bi-patch-check-fill',
            'color': 'primary',
        })

    prestige_count = sum(
        1 for r in results
        if any(s['type'] == 'prestige' for s in r['suggestions'])
    )
    if prestige_count >= max(2, total // 3):
        suggestions.append({
            'criterion': 'experience',
            'label': CRITERIA_LABELS['experience'],
            'message': f'{prestige_count}/{total} candidates come from prestige companies — experience weight matters.',
            'icon': 'bi-award-fill',
            'color': 'success',
        })

    lang_count = sum(1 for r in results if r['lang_score'] > 50)
    if lang_count >= max(2, total // 3):
        suggestions.append({
            'criterion': 'languages',
            'label': CRITERIA_LABELS['languages'],
            'message': f'{lang_count}/{total} candidates score well on languages — adjust weight for this role.',
            'icon': 'bi-translate',
            'color': 'warning',
        })

    flag_count = sum(
        1 for r in results
        if any(s['type'] == 'red_flag' for s in r['suggestions'])
    )
    if flag_count:
        suggestions.append({
            'criterion': None,
            'label': 'Red Flags',
            'message': f'{flag_count}/{total} candidates have red flags — review carefully.',
            'icon': 'bi-exclamation-triangle-fill',
            'color': 'danger',
        })

    return suggestions
