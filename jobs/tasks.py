"""jobs/tasks.py - Zadania Celery dla dopasowania CV do ofert pracy."""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def run_job_match_task(self, match_id):
    """Uruchamia dopasowanie CV do oferty pracy jako zadanie Celery."""
    from jobs.services.matcher import JobMatcher

    try:
        matcher = JobMatcher()
        result = matcher.run_match(match_id)
        return {
            'match_id': str(result.id),
            'status': result.status,
        }
    except Exception as exc:
        logger.error(f"Job match task failed: {exc}")
        raise self.retry(exc=exc)
