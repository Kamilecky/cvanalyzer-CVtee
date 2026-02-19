"""recruitment/tasks.py - Threading wrappers dla przetwarzania w tle.

Używa thread_manager z semaphore (MAX_THREADS=5).
"""

import logging

from analysis.services.thread_manager import run_with_limit

logger = logging.getLogger(__name__)


def run_profile_extraction_in_thread(cv_document_id, user_id):
    """Ekstrakcja profilu kandydata w osobnym wątku."""
    return run_with_limit(
        _run_profile_extraction,
        args=(cv_document_id, user_id),
        name=f'profile-{str(cv_document_id)[:8]}',
    )


def _run_profile_extraction(cv_document_id, user_id):
    from cv.models import CVDocument
    from accounts.models import User
    from recruitment.services.profile_extractor import ProfileExtractor

    try:
        cv_doc = CVDocument.objects.get(id=cv_document_id)
        user = User.objects.get(id=user_id)
        extractor = ProfileExtractor()
        extractor.extract_profile(cv_doc, user)
    except Exception as e:
        logger.error(f"Profile extraction thread failed: {e}")


def run_position_match_in_thread(fit_result_id):
    """Matching kandydata do stanowiska w osobnym wątku."""
    return run_with_limit(
        _run_position_match,
        args=(fit_result_id,),
        name=f'match-{str(fit_result_id)[:8]}',
    )


def _run_position_match(fit_result_id):
    from recruitment.services.position_matcher import PositionMatcher

    try:
        matcher = PositionMatcher()
        matcher.match_single(fit_result_id)
    except Exception as e:
        logger.error(f"Position match thread failed: {e}")


def run_bulk_matching_in_thread(candidate_profile_id, user_id):
    """Matching kandydata do WSZYSTKICH aktywnych stanowisk w tle."""
    return run_with_limit(
        _run_bulk_matching,
        args=(candidate_profile_id, user_id),
        name=f'bulk-{str(candidate_profile_id)[:8]}',
    )


def _run_bulk_matching(candidate_profile_id, user_id):
    """Używa batch matching: 1 request AI = do 10 stanowisk naraz."""
    from recruitment.models import CandidateProfile
    from accounts.models import User
    from recruitment.services.position_matcher import PositionMatcher

    try:
        profile = CandidateProfile.objects.get(id=candidate_profile_id)
        user = User.objects.get(id=user_id)
        matcher = PositionMatcher()
        matcher.match_all_positions(profile, user)

    except Exception as e:
        logger.error(f"Bulk matching thread failed: {e}")


def run_selective_matching_in_thread(candidate_profile_id, user_id, position_ids):
    """Matching kandydata do WYBRANYCH stanowisk w tle."""
    return run_with_limit(
        _run_selective_matching,
        args=(candidate_profile_id, user_id, position_ids),
        name=f'selective-{str(candidate_profile_id)[:8]}',
    )


def _run_selective_matching(candidate_profile_id, user_id, position_ids):
    from recruitment.models import CandidateProfile
    from accounts.models import User
    from recruitment.services.position_matcher import PositionMatcher

    try:
        profile = CandidateProfile.objects.get(id=candidate_profile_id)
        user = User.objects.get(id=user_id)
        matcher = PositionMatcher()
        matcher.match_selected_positions(profile, user, position_ids)

    except Exception as e:
        logger.error(f"Selective matching thread failed: {e}")
