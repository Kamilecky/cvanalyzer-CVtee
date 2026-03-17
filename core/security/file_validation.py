"""core/security/file_validation.py - Secure file upload validation.

Uses python-magic (libmagic) for MIME detection from file content,
not from extension or Content-Type header.

Falls back to manual magic-bytes check when libmagic is unavailable
(e.g. Windows dev environment without libmagic DLL).
"""

import logging

logger = logging.getLogger(__name__)

try:
    import magic as _magic
    _HAS_LIBMAGIC = True
except (ImportError, OSError):
    _HAS_LIBMAGIC = False
    logger.warning(
        "python-magic / libmagic not available — falling back to magic-bytes check. "
        "Install python-magic (Linux) or python-magic-bin (Windows) for full MIME detection."
    )

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

# Magic bytes that identify each allowed type
_MAGIC_BYTES = {
    b'%PDF': 'application/pdf',
    b'PK\x03\x04': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def _detect_mime_fallback(header: bytes) -> str:
    """Detect MIME type from magic bytes when libmagic is not available."""
    for signature, mime in _MAGIC_BYTES.items():
        if header.startswith(signature):
            return mime
    return "application/octet-stream"


def validate_uploaded_file(file) -> bool:
    """Validate file size and MIME type.

    Args:
        file: Django InMemoryUploadedFile / TemporaryUploadedFile

    Returns:
        True if valid.

    Raises:
        ValueError: with a user-safe message if validation fails.
    """
    # 1. Size check (fast — no I/O)
    if file.size > MAX_FILE_SIZE:
        logger.warning(
            f"Upload rejected: file too large ({file.size} bytes, limit {MAX_FILE_SIZE})"
        )
        raise ValueError("File too large. Maximum size is 5 MB.")

    # 2. Read header bytes for MIME detection
    header = file.read(2048)
    file.seek(0)

    # 3. MIME detection
    if _HAS_LIBMAGIC:
        mime = _magic.from_buffer(header, mime=True)
    else:
        mime = _detect_mime_fallback(header)

    if mime not in ALLOWED_MIME_TYPES:
        logger.warning(
            f"Upload rejected: invalid MIME type {mime!r} "
            f"(filename hint: {getattr(file, 'name', 'unknown')})"
        )
        raise ValueError(
            f"Invalid file type detected: {mime}. Only PDF and DOCX files are allowed."
        )

    return True
