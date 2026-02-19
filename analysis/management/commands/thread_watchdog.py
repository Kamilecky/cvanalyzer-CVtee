"""Management command: oznacza stuck analyses/profiles/fits jako failed."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from analysis.models import AnalysisResult
from recruitment.models import CandidateProfile, JobFitResult


class Command(BaseCommand):
    help = 'Mark stuck processing tasks (>10 min) as failed.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--minutes', type=int, default=10,
            help='Timeout threshold in minutes (default: 10)',
        )

    def handle(self, *args, **options):
        minutes = options['minutes']
        cutoff = timezone.now() - timedelta(minutes=minutes)
        total = 0

        # AnalysisResult
        stuck_analyses = AnalysisResult.objects.filter(
            status='processing',
            created_at__lt=cutoff,
        )
        count = stuck_analyses.count()
        if count:
            stuck_analyses.update(
                status='failed',
                error_message=f'Watchdog: stuck in processing for >{minutes} min.',
            )
            self.stdout.write(f'  Marked {count} stuck analyses as failed.')
            total += count

        # CandidateProfile
        stuck_profiles = CandidateProfile.objects.filter(
            status='processing',
            created_at__lt=cutoff,
        )
        count = stuck_profiles.count()
        if count:
            stuck_profiles.update(
                status='failed',
                error_message=f'Watchdog: stuck in processing for >{minutes} min.',
            )
            self.stdout.write(f'  Marked {count} stuck profiles as failed.')
            total += count

        # JobFitResult
        stuck_fits = JobFitResult.objects.filter(
            status='processing',
            created_at__lt=cutoff,
        )
        count = stuck_fits.count()
        if count:
            stuck_fits.update(
                status='failed',
                error_message=f'Watchdog: stuck in processing for >{minutes} min.',
            )
            self.stdout.write(f'  Marked {count} stuck fit results as failed.')
            total += count

        if total == 0:
            self.stdout.write(self.style.SUCCESS('No stuck tasks found.'))
        else:
            self.stdout.write(self.style.WARNING(f'Total: {total} tasks marked as failed.'))
