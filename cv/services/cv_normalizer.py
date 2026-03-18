"""cv/services/cv_normalizer.py — Text normalization for upload-time injection detection.

Produces a clean, lowercase, stripped version of CV text suitable for pattern matching.
The original parsed text is stored in CVDocument.extracted_text unchanged.
This normalized copy is used only for detection — never persisted, never shown to users.
"""

import base64
import binascii
import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

# ── Compiled patterns ────────────────────────────────────────────────────────

_HTML_COMMENT  = re.compile(r'<!--.*?-->', re.DOTALL)
_HTML_TAG      = re.compile(r'<[^>]{0,300}>', re.DOTALL)
_ZERO_WIDTH    = re.compile(r'[\u200b\u200c\u200d\u2060\ufeff\u00ad\u200e\u200f]')
_WHITESPACE    = re.compile(r'[ \t\r\f\v]+')
_MULTI_NEWLINE = re.compile(r'\n{3,}')
# Base64 blobs ≥ 40 chars (long enough to hide an instruction)
_BASE64_BLOB   = re.compile(r'(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9+/])')


def _try_decode_base64(blob: str) -> str:
    """Attempt to decode a base64 blob.  Returns decoded ASCII if printable, else original."""
    try:
        decoded = base64.b64decode(blob + '==').decode('utf-8', errors='ignore')
        printable = sum(c.isprintable() for c in decoded)
        if decoded and printable / len(decoded) > 0.70:
            logger.debug("cv_normalizer: decoded base64 (%d chars) → %r", len(blob), decoded[:60])
            return decoded
    except (binascii.Error, ValueError):
        pass
    return blob


def normalize_text(text: str, max_length: int = 8000) -> str:
    """Return a clean, lowercase version of *text* for injection detection.

    Pipeline:
        1. Unicode NFKC — neutralise homoglyphs and encoding anomalies
        2. Strip HTML comments & tags — can hide instructions in DOCX metadata
        3. Remove zero-width / invisible characters — steganographic channels
        4. Decode base64 fragments — obfuscated payloads decoded before scanning
        5. Collapse whitespace — remove formatting tricks that split keywords
        6. Lowercase — case-insensitive matching downstream
        7. Truncate — cap input to avoid token-exhaustion attacks

    Args:
        text:       Raw extracted CV text from CVParser.
        max_length: Hard cap; default 8 000 chars (≈2× analysis limit).

    Returns:
        Normalised string.  Never raises; returns '' on empty/None input.
    """
    if not text:
        return ''

    # 1. NFKC normalisation
    text = unicodedata.normalize('NFKC', text)

    # 2. HTML removal
    text = _HTML_COMMENT.sub(' ', text)
    text = _HTML_TAG.sub(' ', text)

    # 3. Zero-width removal
    text = _ZERO_WIDTH.sub('', text)

    # 4. Decode base64 blobs before scanning
    text = _BASE64_BLOB.sub(lambda m: _try_decode_base64(m.group()), text)

    # 5. Collapse whitespace (keep newlines for structural analysis)
    text = _WHITESPACE.sub(' ', text)
    text = _MULTI_NEWLINE.sub('\n\n', text)

    # 6. Lowercase
    text = text.lower()

    # 7. Truncate
    if len(text) > max_length:
        text = text[:max_length]

    return text.strip()
