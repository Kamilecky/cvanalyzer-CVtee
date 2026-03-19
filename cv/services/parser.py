"""
cv/services/parser.py - Parser dokumentów CV.

Obsługuje ekstrakcję tekstu z plików PDF, DOCX i TXT
z automatycznym wykrywaniem kodowania (chardet).

Parsing is protected by a 10-second timeout. On Linux/macOS signal.SIGALRM
is used (accurate, works in the main request thread). On Windows a
daemon-thread approach is used as a fallback.
"""

import logging
import platform
import signal
import threading

import chardet

logger = logging.getLogger(__name__)

_PARSE_TIMEOUT_SECONDS = 10
_IS_UNIX = platform.system() != 'Windows'


def _parse_with_timeout(fn, *args):
    """Run fn(*args) with a hard timeout. Raises TimeoutError on expiry."""
    if _IS_UNIX:
        # signal.SIGALRM is accurate and works in the main thread on Unix
        def _handler(signum, frame):
            raise TimeoutError("File processing timeout")

        old_handler = signal.signal(signal.SIGALRM, _handler)
        signal.alarm(_PARSE_TIMEOUT_SECONDS)
        try:
            return fn(*args)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        # Windows fallback: daemon thread with join timeout
        result = [None]
        exc = [None]

        def target():
            try:
                result[0] = fn(*args)
            except Exception as e:
                exc[0] = e

        t = threading.Thread(target=target, daemon=True)
        t.start()
        t.join(_PARSE_TIMEOUT_SECONDS)
        if t.is_alive():
            raise TimeoutError("File processing timeout")
        if exc[0]:
            raise exc[0]
        return result[0]

# Magic bytes for MIME type validation
MIME_SIGNATURES = {
    'pdf': b'%PDF',
    'docx': b'PK\x03\x04',
}


class CVParser:
    """Ekstrakcja tekstu z plików CV (PDF, DOCX, TXT)."""

    SUPPORTED_FORMATS = ['pdf', 'docx', 'txt']
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

    @staticmethod
    def detect_format(filename):
        """Rozpoznaje format na podstawie rozszerzenia pliku."""
        ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
        return ext if ext in CVParser.SUPPORTED_FORMATS else None

    @staticmethod
    def validate_mime(file_obj, fmt):
        """Waliduje plik po magic bytes. Zwraca (is_valid, error_message)."""
        if fmt not in MIME_SIGNATURES:
            return True, ''  # TXT — brak sygnatury

        file_obj.seek(0)
        header = file_obj.read(8)
        file_obj.seek(0)

        expected = MIME_SIGNATURES[fmt]
        if not header.startswith(expected):
            logger.warning(f"MIME mismatch: expected {fmt} signature, got {header[:8]!r}")
            return False, f'File content does not match .{fmt} format. The file may be corrupted or renamed.'
        return True, ''

    @staticmethod
    def validate_file(file_obj, filename):
        """Waliduje plik (format + rozmiar + MIME + size>0). Zwraca (is_valid, error_message)."""
        fmt = CVParser.detect_format(filename)
        if not fmt:
            return False, f'Unsupported format. Please upload PDF, DOCX, or TXT.'
        if hasattr(file_obj, 'size') and file_obj.size == 0:
            return False, 'File is empty. Please upload a valid document.'
        if hasattr(file_obj, 'size') and file_obj.size > CVParser.MAX_FILE_SIZE:
            return False, f'File is too large. Maximum size is 10 MB.'

        # MIME type validation via magic bytes
        is_valid_mime, mime_error = CVParser.validate_mime(file_obj, fmt)
        if not is_valid_mime:
            return False, mime_error

        return True, ''

    @staticmethod
    def parse(file_obj, filename):
        """Główna metoda parsowania. Zwraca dict z text, format, error, hidden_text."""
        from .hidden_text_detector import detect_hidden_text

        fmt = CVParser.detect_format(filename)
        if not fmt:
            return {'text': '', 'format': None, 'error': 'Unsupported format', 'hidden_text': []}

        def _do_parse():
            if fmt == 'pdf':
                return CVParser.parse_pdf(file_obj)
            elif fmt == 'docx':
                return CVParser.parse_docx(file_obj)
            else:
                return CVParser.parse_txt(file_obj)

        try:
            text = _parse_with_timeout(_do_parse)
        except TimeoutError:
            logger.warning(f"Parsing timeout exceeded for file format={fmt}")
            return {'text': '', 'format': fmt, 'error': 'File processing timeout', 'hidden_text': []}
        except Exception as e:
            logger.warning(f"Parsing error for format={fmt}: {e}")
            return {'text': '', 'format': fmt, 'error': str(e), 'hidden_text': []}

        # Skanuj ukryty tekst po udanym parsowaniu (osobny seek, nie blokuje tekstu)
        hidden_findings = []
        try:
            hidden_findings = _parse_with_timeout(detect_hidden_text, file_obj, fmt)
        except TimeoutError:
            logger.warning(f"Hidden text detection timeout for format={fmt}")
        except Exception as e:
            logger.warning(f"Hidden text detection error for format={fmt}: {e}")

        return {
            'text':        text.strip(),
            'format':      fmt,
            'error':       '',
            'hidden_text': hidden_findings,
        }

    @staticmethod
    def parse_pdf(file_obj):
        """Ekstrakcja tekstu z PDF przy użyciu pdfplumber (szybszy i dokładniejszy)."""
        import pdfplumber

        file_obj.seek(0)
        text_parts = []
        with pdfplumber.open(file_obj) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return '\n\n'.join(text_parts)

    @staticmethod
    def _check_zip_bomb(file_obj, max_ratio: float = 100.0, max_uncompressed: int = 50 * 1024 * 1024):
        """Sprawdza DOCX (ZIP) pod kątem zip bomb.

        Args:
            file_obj:         plik do sprawdzenia
            max_ratio:        maksymalny stosunek rozmiar_rozpakowany / rozmiar_skompresowany
            max_uncompressed: maksymalny łączny rozmiar rozpakowanej zawartości (50 MB)

        Raises:
            ValueError: gdy wykryto potencjalną zip bomb
        """
        import zipfile
        file_obj.seek(0)
        try:
            with zipfile.ZipFile(file_obj) as zf:
                total_compressed   = sum(info.compress_size   for info in zf.infolist())
                total_uncompressed = sum(info.file_size        for info in zf.infolist())

                if total_uncompressed > max_uncompressed:
                    logger.warning(
                        f"Zip bomb detected: uncompressed={total_uncompressed} bytes "
                        f"> max={max_uncompressed}"
                    )
                    raise ValueError(
                        f"File rejected: uncompressed size {total_uncompressed // 1024 // 1024} MB "
                        f"exceeds limit."
                    )

                if total_compressed > 0:
                    ratio = total_uncompressed / total_compressed
                    if ratio > max_ratio:
                        logger.warning(
                            f"Zip bomb detected: compression ratio={ratio:.1f} > max={max_ratio}"
                        )
                        raise ValueError(
                            f"File rejected: suspicious compression ratio {ratio:.0f}:1."
                        )
        except zipfile.BadZipFile as e:
            logger.warning(f"DOCX is not a valid ZIP: {e}")
            raise ValueError("File is not a valid DOCX (bad ZIP structure).") from e
        finally:
            file_obj.seek(0)

    @staticmethod
    def parse_docx(file_obj):
        """Ekstrakcja tekstu z DOCX przy użyciu python-docx (z detekcją zip bomb)."""
        from docx import Document

        # Sprawdź zip bomb przed parsowaniem
        CVParser._check_zip_bomb(file_obj)

        file_obj.seek(0)
        doc = Document(file_obj)
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        return '\n'.join(text_parts)

    @staticmethod
    def parse_txt(file_obj):
        """Odczyt pliku tekstowego z automatycznym wykrywaniem kodowania."""
        file_obj.seek(0)
        raw = file_obj.read()
        if isinstance(raw, str):
            return raw

        detected = chardet.detect(raw)
        encoding = detected.get('encoding', 'utf-8') or 'utf-8'
        return raw.decode(encoding, errors='replace')
