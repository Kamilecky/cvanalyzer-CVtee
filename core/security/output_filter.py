"""core/security/output_filter.py - Filtr wyjścia AI przed zapisem do bazy.

Blokuje potencjalny wyciek danych systemowych lub danych innych użytkowników
z odpowiedzi modelu AI — ostatnia linia obrony po stronie backendu.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Frazy których AI nigdy nie powinno zwracać w kontekście CV
_BLOCKED_PHRASES = [
    r'system\s+prompt',
    r'other\s+candidates?',
    r'api[\s_-]?key',
    r'secret[\s_-]?key',
    r'database\s+(schema|query|table)',
    r'SELECT\s+\*?\s+FROM',   # SQL leak
    r'settings\.(py|SECRET)',
    r'os\.environ',
    r'OPENAI_API_KEY',
    r'STRIPE_SECRET',
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _BLOCKED_PHRASES]


def filter_ai_output(text: str, context: str = '') -> str:
    """
    Skanuje tekst wyjściowy AI pod kątem wycieków danych.

    - Jeśli wykryje zablokowaną frazę: usuwa ją i loguje.
    - Nie rzuca wyjątku — analiza jest zapisywana z ostrzeżeniem.

    Args:
        text:    tekst do przefiltrowania (np. summary, analysis_text)
        context: opis skąd pochodzi tekst (do logów)

    Returns:
        Przefiltrowany tekst (zablokowane fragmenty zastąpione placeholderem).
    """
    if not text:
        return text

    modified = False
    for pattern in _COMPILED:
        if pattern.search(text):
            logger.warning(
                f"Output filter: blocked phrase detected in {context!r}: "
                f"pattern={pattern.pattern!r}"
            )
            text = pattern.sub('[REDACTED]', text)
            modified = True

    if modified:
        logger.warning(f"Output filter: text was redacted in {context!r}")

    return text


def filter_dict(data: dict, fields: list[str] | None = None) -> dict:
    """
    Filtruje wybrane pola słownika (np. wynik JSON z AI).

    Args:
        data:   słownik z danymi AI (np. extraction_data)
        fields: lista kluczy do filtrowania; None = filtruj wszystkie str-values

    Returns:
        Słownik z przefiltrowanymi wartościami.
    """
    if not isinstance(data, dict):
        return data

    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            if fields is None or key in fields:
                result[key] = filter_ai_output(value, context=f'field:{key}')
            else:
                result[key] = value
        elif isinstance(value, list):
            result[key] = [
                filter_dict(item) if isinstance(item, dict)
                else filter_ai_output(item, context=f'field:{key}') if isinstance(item, str)
                else item
                for item in value
            ]
        elif isinstance(value, dict):
            result[key] = filter_dict(value, fields)
        else:
            result[key] = value

    return result
