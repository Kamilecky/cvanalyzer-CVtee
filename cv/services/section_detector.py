"""
cv/services/section_detector.py - Inteligentny detektor sekcji CV.

5-etapowy pipeline do wykrywania sekcji z OCR-owego tekstu CV:
1. Normalizacja tekstu (spaced headers, broken words)
2. Wykrywanie nagłówków (słownik PL+EN, fuzzy matching)
3. Heurystyczne wykrywanie nagłówków (formatowanie)
4. Segmentacja dokumentu
5. Mapowanie na kategorie systemowe + fallback heurystyki
"""

import re
import unicodedata


class SectionDetector:
    """Wykrywanie sekcji CV — OCR-aware, PL+EN, heuristic scoring."""

    # ---------------------------------------------------------------
    # Słownik nagłówków: section_type -> list of keywords (lowercase)
    # ---------------------------------------------------------------
    SECTION_KEYWORDS = {
        'summary': [
            'summary', 'profile', 'about me', 'about', 'objective',
            'personal statement', 'professional summary', 'overview',
            'personal profile', 'career objective', 'career summary',
            'podsumowanie', 'profil', 'profil zawodowy', 'o mnie',
            'cel zawodowy', 'opis', 'charakterystyka',
        ],
        'experience': [
            'experience', 'employment', 'work history',
            'professional experience', 'work experience', 'career history',
            'employment history', 'career', 'positions held',
            'doswiadczenie', 'doświadczenie', 'doświadczenie zawodowe',
            'historia zatrudnienia', 'przebieg kariery',
            'doswiadczenie zawodowe',
        ],
        'education': [
            'education', 'academic', 'qualifications', 'degrees',
            'academic background', 'training', 'academic qualifications',
            'edukacja', 'wyksztalcenie', 'wykształcenie', 'szkolenia',
            'szkolenia i kursy', 'kwalifikacje',
        ],
        'skills': [
            'skills', 'competencies', 'technical skills', 'technologies',
            'core competencies', 'key skills', 'expertise',
            'it skills', 'hard skills', 'soft skills',
            'tools', 'tools and technologies',
            'umiejetnosci', 'umiejętności', 'kompetencje',
            'technologie', 'narzedzia', 'narzędzia',
            'umiejetnosci techniczne', 'umiejętności techniczne',
        ],
        'projects': [
            'projects', 'portfolio', 'personal projects', 'key projects',
            'projekty', 'realizacje',
        ],
        'certificates': [
            'certificates', 'certifications', 'licenses',
            'accreditations', 'professional development',
            'certyfikaty', 'licencje', 'kursy', 'kursy i certyfikaty',
        ],
        'languages': [
            'languages', 'language skills', 'foreign languages',
            'jezyki', 'języki', 'jezyki obce', 'języki obce',
            'znajomosc jezykow', 'znajomość języków',
        ],
        'contact': [
            'contact', 'contact information', 'contact details',
            'personal information', 'personal details',
            'kontakt', 'dane kontaktowe', 'dane osobowe',
            'informacje kontaktowe',
        ],
        'interests': [
            'interests', 'hobbies', 'activities',
            'zainteresowania', 'hobby', 'pasje',
        ],
    }

    # ---------------------------------------------------------------
    # ETAP 1: Normalizacja tekstu OCR
    # ---------------------------------------------------------------

    @staticmethod
    def normalize_ocr_text(text):
        """Naprawia typowe problemy OCR: spaced headers, nadmiarowe spacje."""
        lines = text.split('\n')
        normalized = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                normalized.append('')
                continue

            # Sprawdź czy linia to "spaced header" (D O Ś W I A D C Z E N I E)
            if SectionDetector._is_spaced_header(stripped):
                collapsed = SectionDetector._collapse_spaced(stripped)
                normalized.append(collapsed)
            else:
                normalized.append(stripped)

        return '\n'.join(normalized)

    @staticmethod
    def _is_spaced_header(line):
        """Czy linia to nagłówek ze spacjami między literami?

        Heurystyka:
        - >=70% znaków (bez spacji) to pojedyncze litery oddzielone spacją
        - Brak znaków interpunkcyjnych (.,;:!?)
        - Długość > 5 znaków (po stripie)
        - Max 4 słowa po collapsie
        """
        if len(line) < 5:
            return False

        # Nie zawiera interpunkcji typowej dla zdań
        if re.search(r'[.,;:!?\(\)\[\]{}]', line):
            return False

        # Usuń spacje i policz
        chars = list(line)
        if not chars:
            return False

        # Wzorzec: litera spacja litera spacja ...
        # Sprawdzamy czy pary (char, space) dominują
        single_letter_count = 0
        i = 0
        while i < len(chars):
            if chars[i] != ' ':
                # Sprawdź czy to pojedyncza litera (następny to spacja lub koniec)
                is_single = (
                    (i + 1 >= len(chars) or chars[i + 1] == ' ')
                    and (i == 0 or chars[i - 1] == ' ')
                )
                if is_single:
                    single_letter_count += 1
            i += 1

        non_space = sum(1 for c in chars if c != ' ')
        if non_space == 0:
            return False

        ratio = single_letter_count / non_space

        if ratio < 0.70:
            return False

        # Po collapsie nie powinno być więcej niż 4 słowa
        collapsed = SectionDetector._collapse_spaced(line)
        if len(collapsed.split()) > 4:
            return False

        return True

    # Znane słowa PL+EN do rozdzielania zlepionych nagłówków OCR
    _KNOWN_WORDS = [
        'cel', 'zawodowy', 'doświadczenie', 'doswiadczenie', 'zawodowe',
        'umiejętności', 'umiejetnosci', 'techniczne',
        'edukacja', 'wykształcenie', 'wyksztalcenie',
        'języki', 'jezyki', 'obce',
        'kontakt', 'dane', 'kontaktowe', 'osobowe',
        'zainteresowania', 'hobby', 'pasje',
        'certyfikaty', 'kursy', 'licencje',
        'projekty', 'realizacje',
        'podsumowanie', 'profil',
        'experience', 'work', 'professional',
        'education', 'skills', 'languages', 'contact',
        'summary', 'profile', 'projects', 'certificates',
        'interests', 'hobbies', 'objective',
        'informacje', 'dodatkowe',
    ]

    @staticmethod
    def _collapse_spaced(line):
        """Zamienia 'D O Ś W I A D C Z E N I E' → 'DOŚWIADCZENIE'.

        Obsługuje też wielosłowowe: 'C E L  Z A W O D O W Y' → 'CEL ZAWODOWY'
        (podwójna spacja = granica słowa).
        Gdy brak podwójnej spacji, próbuje rozdzielić wg znanych słów.
        """
        # Podwójna+ spacja = granica słowa
        parts = re.split(r' {2,}', line.strip())

        if len(parts) > 1:
            # Są wyraźne granice słów
            result_words = []
            for word in parts:
                collapsed = word.replace(' ', '')
                if collapsed:
                    result_words.append(collapsed)
            return ' '.join(result_words)

        # Brak podwójnej spacji — wszystko zlewa się w jedno
        blob = line.replace(' ', '')
        if not blob:
            return ''

        # Spróbuj rozdzielić blob wg znanych słów
        split = SectionDetector._split_known_words(blob)
        if split:
            return ' '.join(split)

        return blob

    @staticmethod
    def _split_known_words(blob):
        """Próbuje rozdzielić 'CELZAWODOWY' → ['CEL', 'ZAWODOWY'] wg słownika."""
        blob_lower = SectionDetector._strip_diacritics(blob.lower())

        known = SectionDetector._KNOWN_WORDS
        known_normalized = [
            (SectionDetector._strip_diacritics(w.lower()), w) for w in known
        ]
        # Sortuj od najdłuższych (greedy match)
        known_normalized.sort(key=lambda x: -len(x[0]))

        result = []
        remaining = blob_lower
        original = blob

        while remaining:
            matched = False
            for norm, orig_word in known_normalized:
                if remaining.startswith(norm):
                    # Zachowaj oryginalną wielkość liter z blob
                    chunk = original[:len(norm)]
                    result.append(chunk)
                    remaining = remaining[len(norm):]
                    original = original[len(norm):]
                    matched = True
                    break
            if not matched:
                # Nie udało się dopasować — zwróć None
                return None

        return result if len(result) > 1 else None

    # ---------------------------------------------------------------
    # ETAP 2+3: Wykrywanie nagłówków sekcji
    # ---------------------------------------------------------------

    @staticmethod
    def _strip_diacritics(text):
        """Usuwa polskie znaki diakrytyczne do porównania."""
        nfkd = unicodedata.normalize('NFKD', text)
        return ''.join(c for c in nfkd if unicodedata.category(c) != 'Mn')

    @staticmethod
    def _levenshtein(s1, s2):
        """Odległość Levenshteina — proste DP."""
        if len(s1) < len(s2):
            return SectionDetector._levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)

        prev_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            curr_row = [i + 1]
            for j, c2 in enumerate(s2):
                cost = 0 if c1 == c2 else 1
                curr_row.append(min(
                    curr_row[j] + 1,       # insert
                    prev_row[j + 1] + 1,   # delete
                    prev_row[j] + cost,     # replace
                ))
            prev_row = curr_row

        return prev_row[-1]

    @staticmethod
    def classify_heading(heading):
        """Klasyfikuje nagłówek do typu sekcji.

        Metody (w kolejności priorytetu):
        1. Exact match (case-insensitive)
        2. Contains match
        3. Fuzzy match (Levenshtein ≤ 2) z ignorowaniem polskich znaków
        """
        heading_lower = heading.lower().strip()
        # Usuń numerację i znaki specjalne na początku
        heading_clean = re.sub(r'^[\d\.\-\*\#\>\|:]+\s*', '', heading_lower)
        heading_clean = heading_clean.strip()

        if not heading_clean or len(heading_clean) < 3:
            return None

        heading_no_diacritics = SectionDetector._strip_diacritics(heading_clean)

        # 1. Exact match
        for section_type, keywords in SectionDetector.SECTION_KEYWORDS.items():
            for kw in keywords:
                if heading_clean == kw:
                    return section_type

        # 2. Contains match (heading zawiera keyword lub keyword zawiera heading)
        for section_type, keywords in SectionDetector.SECTION_KEYWORDS.items():
            for kw in keywords:
                if kw in heading_clean or heading_clean in kw:
                    return section_type

        # 3. Fuzzy match: Levenshtein ≤ 2 (ignorując diakrytyki)
        best_match = None
        best_dist = 3  # max dopuszczalna odległość + 1
        for section_type, keywords in SectionDetector.SECTION_KEYWORDS.items():
            for kw in keywords:
                kw_no_diacritics = SectionDetector._strip_diacritics(kw)
                dist = SectionDetector._levenshtein(
                    heading_no_diacritics, kw_no_diacritics,
                )
                if dist < best_dist:
                    best_dist = dist
                    best_match = section_type

        if best_match and best_dist <= 2:
            return best_match

        return None

    @staticmethod
    def classify_multi_headers(heading):
        """Próbuje rozdzielić zlepione nagłówki OCR, np. 'HOBBY EDUKACJA'.

        Returns:
            list of (title, section_type) tuples, or None if not multi-header.
        """
        words = heading.strip().split()
        if len(words) < 2 or len(words) > 4:
            return None

        # Spróbuj podzielić na 2 części w każdym możliwym miejscu
        results = []
        for split_at in range(1, len(words)):
            part1 = ' '.join(words[:split_at])
            part2 = ' '.join(words[split_at:])
            type1 = SectionDetector.classify_heading(part1)
            type2 = SectionDetector.classify_heading(part2)
            if type1 and type2 and type1 != type2:
                results = [(part1, type1), (part2, type2)]
                break

        return results if results else None

    @staticmethod
    def _is_formatting_header(line, prev_empty, next_empty):
        """Czy linia wygląda na nagłówek na podstawie formatowania?

        Musi spełniać ≥2 z warunków:
        - Cała wielkimi literami
        - < 4 słów
        - Brak kropki na końcu
        - Długość 3–30 znaków
        - Oddzielona pustą linią (przed lub po)
        """
        stripped = line.strip()
        if not stripped or len(stripped) < 3:
            return False

        score = 0

        # Wielkie litery (ignoruj cyfry i spacje)
        alpha_chars = [c for c in stripped if c.isalpha()]
        if alpha_chars and all(c.isupper() for c in alpha_chars):
            score += 1

        # Mało słów
        word_count = len(stripped.split())
        if word_count < 4:
            score += 1

        # Brak kropki na końcu
        if not stripped.endswith('.'):
            score += 1

        # Odpowiednia długość
        if 3 <= len(stripped) <= 30:
            score += 1

        # Oddzielona pustą linią
        if prev_empty or next_empty:
            score += 1

        return score >= 3

    # ---------------------------------------------------------------
    # ETAP 5: Fallback heurystyki (daty→experience, skills, contact)
    # ---------------------------------------------------------------

    @staticmethod
    def _detect_experience_block(lines):
        """Wykrywa blok doświadczenia po wzorcach dat."""
        date_pattern = re.compile(
            r'(19|20)\d{2}'             # rok
            r'(\s*[-–—/]\s*'            # separator
            r'((19|20)\d{2}|'           # rok końcowy
            r'obecnie|present|current|teraz|nadal'  # lub "obecnie"
            r'))?',
            re.IGNORECASE,
        )
        blocks = []
        current_block_start = None

        for i, line in enumerate(lines):
            stripped = line.strip()
            if date_pattern.search(stripped):
                if current_block_start is None:
                    current_block_start = max(0, i - 1)
            else:
                if current_block_start is not None and i - current_block_start > 2:
                    blocks.append((current_block_start, i))
                    current_block_start = None

        if current_block_start is not None:
            blocks.append((current_block_start, len(lines) - 1))

        return blocks

    @staticmethod
    def _detect_skills_block(lines):
        """Wykrywa blok umiejętności po koncentracji krótkich linii/buzzwordów."""
        tech_keywords = {
            'python', 'java', 'javascript', 'sql', 'excel', 'word',
            'powerpoint', 'sap', 'wms', 'power bi', 'tableau', 'react',
            'angular', 'django', 'flask', 'docker', 'kubernetes', 'aws',
            'azure', 'git', 'linux', 'windows', 'html', 'css', 'c++',
            'c#', '.net', 'php', 'ruby', 'swift', 'kotlin', 'node',
            'typescript', 'mongodb', 'postgresql', 'mysql', 'redis',
            'photoshop', 'illustrator', 'figma', 'autocad', 'matlab',
            'r', 'scala', 'go', 'rust', 'terraform', 'jenkins',
        }
        blocks = []
        current_block_start = None
        consecutive_matches = 0

        for i, line in enumerate(lines):
            stripped = line.strip().lower()
            words = re.split(r'[,;/|\s]+', stripped)
            match_count = sum(1 for w in words if w in tech_keywords)

            if match_count >= 1 or (len(stripped) < 30 and len(words) <= 3 and stripped):
                if current_block_start is None:
                    current_block_start = i
                consecutive_matches += 1
            else:
                if consecutive_matches >= 3:
                    blocks.append((current_block_start, i))
                current_block_start = None
                consecutive_matches = 0

        if consecutive_matches >= 3 and current_block_start is not None:
            blocks.append((current_block_start, len(lines) - 1))

        return blocks

    @staticmethod
    def _detect_contact_block(lines):
        """Wykrywa blok kontaktowy po email, telefon, adres."""
        email_re = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        phone_re = re.compile(r'[\+]?[\d\s\-\(\)]{7,15}')
        url_re = re.compile(r'(linkedin|github|http|www\.)', re.IGNORECASE)

        contact_lines = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if email_re.search(stripped) or phone_re.search(stripped) or url_re.search(stripped):
                contact_lines.append(i)

        if not contact_lines:
            return []

        # Grupuj sąsiednie linie kontaktowe
        blocks = []
        start = contact_lines[0]
        prev = start
        for idx in contact_lines[1:]:
            if idx - prev > 3:
                blocks.append((max(0, start - 1), prev + 1))
                start = idx
            prev = idx
        blocks.append((max(0, start - 1), prev + 1))

        return blocks

    @staticmethod
    def _detect_language_block(lines):
        """Wykrywa blok języków po wzorcach typu 'angielski - B2'."""
        lang_patterns = re.compile(
            r'(angielski|english|niemiecki|german|francuski|french|'
            r'hiszpanski|hiszpański|spanish|wloski|włoski|italian|'
            r'rosyjski|russian|polski|polish|chiński|chinese|'
            r'japoński|japanese|koreański|korean|'
            r'portugalski|portuguese|arabski|arabic|'
            r'ukraiński|ukrainian|czeski|czech|'
            r'native|fluent|advanced|intermediate|basic|'
            r'ojczysty|biegły|biegly|zaawansowany|średniozaawansowany|podstawowy|'
            r'[abc][12]|c1|c2|b1|b2|a1|a2)',
            re.IGNORECASE,
        )

        lang_lines = []
        for i, line in enumerate(lines):
            if lang_patterns.search(line.strip()):
                lang_lines.append(i)

        if len(lang_lines) < 2:
            return []

        # Grupuj
        blocks = []
        start = lang_lines[0]
        prev = start
        for idx in lang_lines[1:]:
            if idx - prev > 3:
                blocks.append((start, prev + 1))
                start = idx
            prev = idx
        blocks.append((start, prev + 1))

        return blocks

    @staticmethod
    def _detect_education_block(lines):
        """Wykrywa blok edukacji po wzorcach szkół/uczelni."""
        edu_patterns = re.compile(
            r'(uniwersytet|university|politechnika|academy|'
            r'liceum|technikum|szkoła|szkola|school|college|'
            r'studia|bachelor|master|magister|inżynier|inzynier|'
            r'licencjat|doktor|phd|mba|'
            r'wydział|wydzial|faculty|institute|instytut)',
            re.IGNORECASE,
        )

        edu_lines = []
        for i, line in enumerate(lines):
            if edu_patterns.search(line.strip()):
                edu_lines.append(i)

        if not edu_lines:
            return []

        blocks = []
        start = edu_lines[0]
        prev = start
        for idx in edu_lines[1:]:
            if idx - prev > 5:
                blocks.append((max(0, start - 1), prev + 2))
                start = idx
            prev = idx
        blocks.append((max(0, start - 1), min(len(lines) - 1, prev + 2)))

        return blocks

    # ---------------------------------------------------------------
    # GŁÓWNA METODA: detect_sections()
    # ---------------------------------------------------------------

    @staticmethod
    def detect_sections(text):
        """Wykrywa sekcje w tekście CV — 5-etapowy pipeline.

        Returns:
            list[dict]: [{type, title, content, start, end, order}, ...]
        """
        if not text or not text.strip():
            return []

        # === ETAP 1: Normalizacja OCR ===
        normalized = SectionDetector.normalize_ocr_text(text)
        lines = normalized.split('\n')

        # === ETAP 1b: Rozdzielanie zlepionych nagłówków OCR ===
        # np. "HOBBY EDUKACJA" → dwie osobne linie "HOBBY" i "EDUKACJA"
        expanded_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and len(stripped) <= 40:
                multi = SectionDetector.classify_multi_headers(stripped)
                if multi:
                    for title, _ in multi:
                        expanded_lines.append(title)
                    continue
            expanded_lines.append(line)
        lines = expanded_lines

        # === ETAP 2+3: Wykrywanie nagłówków (słownik + formatowanie) ===
        header_lines = {}  # line_index -> section_type

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            # Za długie linie nie są nagłówkami
            if len(stripped) > 60:
                continue

            # Etap 2: Klasyfikacja ze słownika (exact, contains, fuzzy)
            section_type = SectionDetector.classify_heading(stripped)
            if section_type:
                header_lines[i] = section_type
                continue

            # Etap 3: Heurystyka formatowania
            prev_empty = (i == 0) or (lines[i - 1].strip() == '')
            next_empty = (i == len(lines) - 1) or (lines[i + 1].strip() == '')

            if SectionDetector._is_formatting_header(stripped, prev_empty, next_empty):
                section_type = SectionDetector.classify_heading(stripped)
                if section_type:
                    header_lines[i] = section_type

        # === ETAP 4: Segmentacja dokumentu ===
        sections = []

        if header_lines:
            sorted_headers = sorted(header_lines.keys())

            # Tekst przed pierwszym nagłówkiem → header/summary
            if sorted_headers[0] > 0:
                pre_content = '\n'.join(lines[:sorted_headers[0]]).strip()
                if pre_content and len(pre_content) > 20:
                    sections.append({
                        'type': 'summary',
                        'title': 'Header',
                        'content': pre_content,
                        'start': 0,
                        'end': sorted_headers[0] - 1,
                        'order': len(sections),
                    })

            # Sekcje z nagłówków
            for idx, header_i in enumerate(sorted_headers):
                next_i = (
                    sorted_headers[idx + 1]
                    if idx + 1 < len(sorted_headers)
                    else len(lines)
                )
                content = '\n'.join(lines[header_i + 1:next_i]).strip()
                sections.append({
                    'type': header_lines[header_i],
                    'title': lines[header_i].strip(),
                    'content': content,
                    'start': header_i,
                    'end': next_i - 1,
                    'order': len(sections),
                })

        # === ETAP 5: Fallback — jeśli <3 sekcji, użyj heurystyk ===
        if len(sections) < 3:
            sections = SectionDetector._apply_fallback_heuristics(
                lines, sections, header_lines,
            )

        # Jeśli nadal brak sekcji → cały tekst jako 'other'
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
    def _apply_fallback_heuristics(lines, existing_sections, header_lines):
        """Fallback: wykrywanie sekcji po zawartości (daty, skills, contact)."""
        claimed = set()
        for s in existing_sections:
            for i in range(s['start'], s['end'] + 1):
                claimed.add(i)

        new_sections = list(existing_sections)

        # Sprawdź czy brakuje experience
        has_experience = any(s['type'] == 'experience' for s in existing_sections)
        if not has_experience:
            for start, end in SectionDetector._detect_experience_block(lines):
                if not any(i in claimed for i in range(start, end + 1)):
                    content = '\n'.join(lines[start:end + 1]).strip()
                    if content:
                        new_sections.append({
                            'type': 'experience',
                            'title': 'Experience (detected)',
                            'content': content,
                            'start': start,
                            'end': end,
                            'order': len(new_sections),
                        })
                        for i in range(start, end + 1):
                            claimed.add(i)
                        break

        # Sprawdź skills
        has_skills = any(s['type'] == 'skills' for s in existing_sections)
        if not has_skills:
            for start, end in SectionDetector._detect_skills_block(lines):
                if not any(i in claimed for i in range(start, end + 1)):
                    content = '\n'.join(lines[start:end + 1]).strip()
                    if content:
                        new_sections.append({
                            'type': 'skills',
                            'title': 'Skills (detected)',
                            'content': content,
                            'start': start,
                            'end': end,
                            'order': len(new_sections),
                        })
                        for i in range(start, end + 1):
                            claimed.add(i)
                        break

        # Sprawdź contact
        has_contact = any(s['type'] == 'contact' for s in existing_sections)
        if not has_contact:
            for start, end in SectionDetector._detect_contact_block(lines):
                if not any(i in claimed for i in range(start, end + 1)):
                    content = '\n'.join(lines[start:end + 1]).strip()
                    if content:
                        new_sections.append({
                            'type': 'contact',
                            'title': 'Contact (detected)',
                            'content': content,
                            'start': start,
                            'end': end,
                            'order': len(new_sections),
                        })
                        for i in range(start, end + 1):
                            claimed.add(i)
                        break

        # Sprawdź languages
        has_languages = any(s['type'] == 'languages' for s in existing_sections)
        if not has_languages:
            for start, end in SectionDetector._detect_language_block(lines):
                if not any(i in claimed for i in range(start, end + 1)):
                    content = '\n'.join(lines[start:end + 1]).strip()
                    if content:
                        new_sections.append({
                            'type': 'languages',
                            'title': 'Languages (detected)',
                            'content': content,
                            'start': start,
                            'end': end,
                            'order': len(new_sections),
                        })
                        for i in range(start, end + 1):
                            claimed.add(i)
                        break

        # Sprawdź education
        has_education = any(s['type'] == 'education' for s in existing_sections)
        if not has_education:
            for start, end in SectionDetector._detect_education_block(lines):
                if not any(i in claimed for i in range(start, end + 1)):
                    content = '\n'.join(lines[start:end + 1]).strip()
                    if content:
                        new_sections.append({
                            'type': 'education',
                            'title': 'Education (detected)',
                            'content': content,
                            'start': start,
                            'end': end,
                            'order': len(new_sections),
                        })
                        for i in range(start, end + 1):
                            claimed.add(i)
                        break

        # Nieprzypisany tekst → other
        unclaimed_lines = [
            lines[i] for i in range(len(lines))
            if i not in claimed and lines[i].strip()
        ]
        if unclaimed_lines and len(new_sections) > 0:
            other_text = '\n'.join(unclaimed_lines).strip()
            if other_text and len(other_text) > 30:
                new_sections.append({
                    'type': 'other',
                    'title': 'Other',
                    'content': other_text,
                    'start': 0,
                    'end': len(lines) - 1,
                    'order': len(new_sections),
                })

        # Sortuj po pozycji w dokumencie
        new_sections.sort(key=lambda s: s['start'])
        for i, s in enumerate(new_sections):
            s['order'] = i

        return new_sections
