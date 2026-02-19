"""analysis/tasks.py - Uruchamianie analizy CV w tle (threading.Thread).

Bez Celery - używa threading.Thread + semaphore (MAX_THREADS=5)
do uruchomienia analizy poza requestem.
"""

import logging

from analysis.services.thread_manager import run_with_limit

logger = logging.getLogger(__name__)


def run_analysis_in_thread(analysis_id):
    """Uruchamia analizę CV w osobnym wątku z limitem."""
    return run_with_limit(
        _run_analysis,
        args=(analysis_id,),
        name=f'analysis-{analysis_id[:8]}',
    )


def _run_analysis(analysis_id):
    """Wrapper dla CVAnalyzer.run_analysis z obsługą błędów."""
    from analysis.services.analyzer import CVAnalyzer

    try:
        analyzer = CVAnalyzer()
        analyzer.run_analysis(analysis_id)
    except Exception as e:
        logger.error(f"Analysis thread failed for {analysis_id}: {e}")


def run_rewrite_in_thread(analysis_id, section_type, original_text):
    """Uruchamia przepisywanie sekcji CV w osobnym wątku z limitem."""
    return run_with_limit(
        _run_rewrite,
        args=(analysis_id, section_type, original_text),
        name=f'rewrite-{analysis_id[:8]}',
    )


def _run_rewrite(analysis_id, section_type, original_text):
    """Wrapper dla CVRewriter.rewrite_section z obsługą błędów."""
    from analysis.services.rewriter import CVRewriter

    try:
        rewriter = CVRewriter()
        rewriter.rewrite_section(analysis_id, section_type, original_text)
    except Exception as e:
        logger.error(f"Rewrite thread failed for {analysis_id}: {e}")
