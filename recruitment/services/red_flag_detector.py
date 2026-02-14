"""recruitment/services/red_flag_detector.py - Wykrywanie red flags w historii zatrudnienia.

Red flags są wykrywane jako część PROFILE_EXTRACTION_PROMPT (zintegrowane).
Ten moduł udostępnia dodatkowe reguły Python-based (bez AI).
"""

import logging

logger = logging.getLogger(__name__)


class RedFlagDetector:
    """Analiza historii pracy pod kątem ryzyk - reguły Python."""

    @staticmethod
    def analyze_companies(companies):
        """Analizuje listę firm kandydata pod kątem red flags.

        Args:
            companies: list of dicts z companies JSON z CandidateProfile

        Returns:
            list of red flag dicts
        """
        flags = []

        if not companies:
            return flags

        # Job hopping: >3 zmiany w 3 lata
        short_stints = [
            c for c in companies
            if c.get('duration_months') and c['duration_months'] < 12
        ]
        if len(short_stints) >= 3:
            flags.append({
                'type': 'job_hopping',
                'severity': 'warning',
                'description': f'{len(short_stints)} positions held for less than 1 year.',
            })

        # Employment gaps: sprawdź luki między firmami
        sorted_companies = sorted(
            [c for c in companies if c.get('end_year')],
            key=lambda c: c.get('start_year', 0),
        )
        for i in range(1, len(sorted_companies)):
            prev_end = sorted_companies[i - 1].get('end_year', 0)
            curr_start = sorted_companies[i].get('start_year', 0)
            if curr_start and prev_end and curr_start - prev_end >= 2:
                flags.append({
                    'type': 'employment_gap',
                    'severity': 'info',
                    'description': f'Gap of ~{curr_start - prev_end} years between positions.',
                })

        return flags
