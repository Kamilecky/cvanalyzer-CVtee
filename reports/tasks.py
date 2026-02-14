"""reports/tasks.py - Zadania Celery dla generowania raportów PDF."""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1, default_retry_delay=15)
def generate_pdf_report_task(self, report_id):
    """Generuje raport PDF jako zadanie Celery."""
    from reports.services.pdf_generator import PDFGenerator

    try:
        result = PDFGenerator.generate(report_id)
        return {
            'report_id': str(result.id),
            'status': result.status,
        }
    except Exception as exc:
        logger.error(f"PDF report task failed: {exc}")
        raise self.retry(exc=exc)
