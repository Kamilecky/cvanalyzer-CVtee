"""analysis/utils.py - Centralna logika uruchamiania analizy CV.

Single source of truth: ta funkcja jest wywoływana zarówno z analysis/views.py
jak i z recruitment/views.py. Obsługuje:
- Sprawdzanie limitu planu (can_analyze)
- Hash-based cache (clone)
- Tworzenie AnalysisResult + uruchomienie wątku
- Inkrementację licznika (use_analysis)
"""

from .models import AnalysisResult
from .services.analyzer import CVAnalyzer
from .tasks import run_analysis_in_thread


def start_cv_analysis(cv_doc, user):
    """Uruchamia analizę CV z cache + billing.

    Args:
        cv_doc: CVDocument instance (must have extracted_text)
        user: User instance

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

    analysis = AnalysisResult.objects.create(
        user=user,
        cv_document=cv_doc,
        status='pending',
    )
    run_analysis_in_thread(str(analysis.id))
    return analysis, 'started'
