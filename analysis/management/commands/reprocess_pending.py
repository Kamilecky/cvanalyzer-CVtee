"""Management command: ponawia analizy z status error/pending_ai starsze niż 1h."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from analysis.models import AnalysisResult
from analysis.tasks import run_analysis_in_thread


class Command(BaseCommand):
    help = 'Reprocess failed/pending_ai analyses older than 1 hour (max 50).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max', type=int, default=50,
            help='Maximum number of analyses to reprocess (default: 50)',
        )
        parser.add_argument(
            '--hours', type=int, default=1,
            help='Minimum age in hours (default: 1)',
        )

    def handle(self, *args, **options):
        max_count = options['max']
        hours = options['hours']
        cutoff = timezone.now() - timedelta(hours=hours)

        analyses = AnalysisResult.objects.filter(
            status__in=['failed', 'pending_ai'],
            created_at__lt=cutoff,
        ).order_by('created_at')[:max_count]

        count = analyses.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No analyses to reprocess.'))
            return

        self.stdout.write(f'Reprocessing {count} analyses...')

        for analysis in analyses:
            analysis.status = 'pending'
            analysis.progress = 0
            analysis.error_message = ''
            analysis.save(update_fields=['status', 'progress', 'error_message'])
            run_analysis_in_thread(str(analysis.id))
            self.stdout.write(f'  Queued: {analysis.id}')

        self.stdout.write(self.style.SUCCESS(f'Done. {count} analyses queued for reprocessing.'))
