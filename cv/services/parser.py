"""
cv/services/parser.py - Parser dokumentów CV.

Obsługuje ekstrakcję tekstu z plików PDF, DOCX i TXT
z automatycznym wykrywaniem kodowania (chardet).
"""

import chardet


class CVParser:
    """Ekstrakcja tekstu z plików CV (PDF, DOCX, TXT)."""

    SUPPORTED_FORMATS = ['pdf', 'docx', 'txt']
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

    @staticmethod
    def detect_format(filename):
        """Rozpoznaje format na podstawie rozszerzenia pliku."""
        ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
        return ext if ext in CVParser.SUPPORTED_FORMATS else None

    @staticmethod
    def validate_file(file_obj, filename):
        """Waliduje plik (format + rozmiar). Zwraca (is_valid, error_message)."""
        fmt = CVParser.detect_format(filename)
        if not fmt:
            return False, f'Unsupported format. Please upload PDF, DOCX, or TXT.'
        if hasattr(file_obj, 'size') and file_obj.size > CVParser.MAX_FILE_SIZE:
            return False, f'File is too large. Maximum size is 10 MB.'
        return True, ''

    @staticmethod
    def parse(file_obj, filename):
        """Główna metoda parsowania. Zwraca dict z text, format, page_count."""
        fmt = CVParser.detect_format(filename)
        if not fmt:
            return {'text': '', 'format': None, 'error': 'Unsupported format'}

        try:
            if fmt == 'pdf':
                text = CVParser.parse_pdf(file_obj)
            elif fmt == 'docx':
                text = CVParser.parse_docx(file_obj)
            else:
                text = CVParser.parse_txt(file_obj)

            return {'text': text.strip(), 'format': fmt, 'error': ''}
        except Exception as e:
            return {'text': '', 'format': fmt, 'error': str(e)}

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
    def parse_docx(file_obj):
        """Ekstrakcja tekstu z DOCX przy użyciu python-docx."""
        from docx import Document

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
