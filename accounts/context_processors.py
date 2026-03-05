"""accounts/context_processors.py - Dane użytkownika dostępne w każdym szablonie."""


def user_stats(request):
    """Dodaje do kontekstu liczbę aktywnych stanowisk użytkownika.

    Wywoływany raz na request; JobPosition importowane wewnątrz funkcji
    żeby uniknąć circular import (accounts ← recruitment).
    """
    if not request.user.is_authenticated:
        return {}

    from recruitment.models import JobPosition
    positions_count = JobPosition.objects.filter(
        user=request.user, is_active=True,
    ).count()

    return {'user_positions_count': positions_count}
