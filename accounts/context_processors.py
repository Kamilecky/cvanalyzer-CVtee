"""accounts/context_processors.py - Dane użytkownika dostępne w każdym szablonie."""

from django.conf import settings


def user_stats(request):
    """Dodaje do kontekstu statystyki użytkownika: liczba stanowisk + limit planu.

    Wywoływany raz na request; JobPosition importowane wewnątrz funkcji
    żeby uniknąć circular import (accounts ← recruitment).
    """
    if not request.user.is_authenticated:
        return {}

    from recruitment.models import JobPosition
    positions_count = JobPosition.objects.filter(
        user=request.user, is_active=True,
    ).count()

    position_limit = settings.JOB_POSITION_LIMITS.get(request.user.plan)

    return {
        'user_positions_count': positions_count,
        'user_position_limit': position_limit,   # None = unlimited
    }
