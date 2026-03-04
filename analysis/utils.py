"""analysis/utils.py - Centralna logika uruchamiania analizy CV.

Single source of truth: ta funkcja jest wywoływana zarówno z analysis/views.py
jak i z recruitment/views.py. Obsługuje:
- Sprawdzanie limitu planu (can_analyze)
- Hash-based cache (clone)
- Tworzenie AnalysisResult + uruchomienie wątku
- Inkrementację licznika (use_analysis)
"""

from django.core.cache import cache

from .models import AnalysisResult
from .services.analyzer import CVAnalyzer
from .tasks import run_analysis_in_thread

HISTORY_CACHE_TTL = 60
_HISTORY_MAX_PAGES = 26  # covers up to 25 pages × 20 items = 500 analyses


def _history_cache_key(user_id, page):
    return f"user_history_{user_id}_{page}"


def invalidate_history_cache(user_id):
    """Clear all cached history pages for a user."""
    cache.delete_many([_history_cache_key(user_id, p) for p in range(1, _HISTORY_MAX_PAGES)])


def start_cv_analysis(cv_doc, user, language='en'):
    """Uruchamia analizę CV z cache + billing.

    Args:
        cv_doc: CVDocument instance (must have extracted_text)
        user: User instance
        language: ISO language code ('en', 'pl') — AI will respond in this language

    Returns:
        (analysis, status) where:
        - analysis: AnalysisResult instance or None
        - status: 'started' | 'cached' | 'limit_reached' | 'no_text'
    """
    if not user.can_analyze():
        return None, 'limit_reached'

    if not cv_doc.extracted_text:
        return None, 'no_text'

    # Hash-based cache
    cached = CVAnalyzer.check_cache(cv_doc)
    if cached:
        cloned = CVAnalyzer.clone_analysis(cached, cv_doc, user)
        user.use_analysis()
        return cloned, 'cached'

    lang = language[:2] if language else 'en'
    analysis = AnalysisResult.objects.create(
        user=user,
        cv_document=cv_doc,
        status='pending',
        raw_ai_response={'_lang': lang},
    )
    invalidate_history_cache(user.id)
    run_analysis_in_thread(str(analysis.id))
    return analysis, 'started'
