"""billing/tasks.py - Zadania Celery dla systemu billing."""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def reset_monthly_usage():
    """Resetuje miesięczne liczniki analiz dla wszystkich użytkowników.

    Uruchamiane automatycznie 1. dnia każdego miesiąca przez Celery Beat.
    """
    from accounts.models import User

    count = User.objects.filter(analyses_used_this_month__gt=0).update(
        analyses_used_this_month=0
    )
    logger.info(f"Monthly usage reset: {count} users affected")
    return {'reset_count': count}
