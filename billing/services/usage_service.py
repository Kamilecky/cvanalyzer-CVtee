"""billing/services/usage_service.py - Śledzenie użycia i limitów."""

from billing.models import UsageRecord


class UsageService:
    """Serwis do śledzenia użycia funkcji i sprawdzania limitów."""

    @staticmethod
    def record_usage(user, action, analysis=None):
        """Rejestruje użycie funkcji."""
        return UsageRecord.objects.create(
            user=user,
            action=action,
            analysis=analysis,
        )

    @staticmethod
    def get_monthly_usage(user, action=None):
        """Zwraca liczbę użyć w bieżącym miesiącu."""
        from django.utils import timezone
        now = timezone.now()
        qs = UsageRecord.objects.filter(
            user=user,
            created_at__year=now.year,
            created_at__month=now.month,
        )
        if action:
            qs = qs.filter(action=action)
        return qs.count()

    @staticmethod
    def get_usage_history(user, limit=50):
        """Zwraca ostatnie rekordy użycia."""
        return UsageRecord.objects.filter(user=user)[:limit]
