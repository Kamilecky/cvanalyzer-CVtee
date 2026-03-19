"""accounts/context_processors.py - Dane użytkownika dostępne w każdym szablonie."""

from django.conf import settings


def user_stats(request):
    """Dodaje do kontekstu statystyki użytkownika: liczba stanowisk + limit planu
    + liczba oflagowanych CV (dla badge w sidebarze).

    Wywoływany raz na request; importy wewnątrz funkcji żeby uniknąć
    circular import (accounts ← recruitment / analysis).
    """
    if not request.user.is_authenticated:
        return {}

    from recruitment.models import JobPosition
    from analysis.models import AnalysisResult

    positions_count = JobPosition.objects.filter(
        user=request.user, is_active=True,
    ).count()

    position_limit = settings.JOB_POSITION_LIMITS.get(request.user.plan)

    # Liczba analiz z wykrytymi flagami (security_flags != [])
    # Używane przez badge w sidebarze obok "Flagged CVs"
    flagged_count = (
        AnalysisResult.objects
        .filter(user=request.user)
        .exclude(security_flags=[])
        .count()
        if request.user.has_feature('recruitment')
        else 0
    )

    return {
        'user_positions_count': positions_count,
        'user_position_limit':  position_limit,   # None = unlimited
        'flagged_cvs_count':    flagged_count,
    }
