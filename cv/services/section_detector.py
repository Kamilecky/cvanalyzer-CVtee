"""
cv/services/section_detector.py - Detektor sekcji CV.

Wykrywa granice sekcji w tekście CV na podstawie słów kluczowych.
Służy jako wstępne przetwarzanie przed analizą AI.
"""

import re


class SectionDetector:
    """Wykrywanie sekcji CV na podstawie nagłówków i słów kluczowych."""

    SECTION_KEYWORDS = {
        'summary': [
            'summary', 'profile', 'about me', 'objective',
            'personal statement', 'professional summary', 'overview',
            'podsumowanie', 'profil', 'o mnie', 'cel zawodowy',
        ],
        'experience': [
            'experience', 'employment', 'work history', 'professional experience',
            'work experience', 'career history',
            'doświadczenie', 'historia zatrudnienia',
        ],
        'education': [
            'education', 'academic', 'qualifications', 'degrees',
            'academic background', 'training',
            'edukacja', 'wykształcenie', 'szkolenia',
        ],
        'skills': [
            'skills', 'competencies', 'technical skills', 'technologies',
            'core competencies', 'key skills', 'expertise',
            'umiejętności', 'kompetencje', 'technologie',
        ],
        'projects': [
            'projects', 'portfolio', 'personal projects', 'key projects',
            'projekty',
        ],
        'certificates': [
            'certificates', 'certifications', 'licenses', 'accreditations',
            'certyfikaty', 'licencje',
        ],
        'languages': [
            'languages', 'języki', 'language skills',
        ],
        'interests': [
            'interests', 'hobbies', 'activities',
            'zainteresowania', 'hobby',
        ],
    }

    @staticmethod
    def detect_sections(text):
        """Wykrywa sekcje w tekście CV.

        Zwraca listę dict: {type, title, content, start, end, order}.
        """
        lines = text.split('\n')
        sections = []
        current_section = None
        current_lines = []
        current_start = 0

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                if current_lines:
                    current_lines.append(line)
                continue

            section_type = SectionDetector.classify_heading(stripped)
            if section_type and len(stripped) < 80:
                # Zapisz poprzednią sekcję
                if current_section:
                    sections.append({
                        'type': current_section['type'],
                        'title': current_section['title'],
                        'content': '\n'.join(current_lines).strip(),
                        'start': current_start,
                        'end': i - 1,
                        'order': len(sections),
                    })

                current_section = {'type': section_type, 'title': stripped}
                current_lines = []
                current_start = i
            else:
                current_lines.append(line)

        # Ostatnia sekcja
        if current_section:
            sections.append({
                'type': current_section['type'],
                'title': current_section['title'],
                'content': '\n'.join(current_lines).strip(),
                'start': current_start,
                'end': len(lines) - 1,
                'order': len(sections),
            })

        # Jeśli nie wykryto żadnych sekcji, cały tekst jako 'other'
        if not sections and text.strip():
            sections.append({
                'type': 'other',
                'title': 'Full Document',
                'content': text.strip(),
                'start': 0,
                'end': len(lines) - 1,
                'order': 0,
            })

        return sections

    @staticmethod
    def classify_heading(heading):
        """Klasyfikuje nagłówek do typu sekcji."""
        heading_lower = heading.lower().strip()
        # Usuń numerację i znaki specjalne
        heading_clean = re.sub(r'^[\d\.\-\*\#\>\|]+\s*', '', heading_lower)

        for section_type, keywords in SectionDetector.SECTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in heading_clean:
                    return section_type

        return None
