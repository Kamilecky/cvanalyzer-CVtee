"""analysis/services/prompts.py - Prompty dla OpenAI GPT.

Pipeline:
1. EXTRACTION_PROMPT - ekstrakcja danych + wykrywanie problemow → JSON
2. SECTION_ANALYSIS_PROMPT - jakosciowa analiza sekcji CV → JSON (bez ocen numerycznych)

Wszystkie prompty dopasowania zawieraja reguly semantyczne:
synonimy, formy gramatyczne i odpowiedniki PL/EN traktowane jako pelne dopasowanie.
"""

SYSTEM_PROMPT = "You are a CV analyst. Respond only in valid JSON."

# ---------------------------------------------------------------------------
# Blok regul semantycznych wstawiany do promptow dopasowania
# ---------------------------------------------------------------------------
_SEMANTIC_RULES = """SEMANTIC MATCHING RULES (apply to ALL skill and requirement comparisons):
1. Treat semantically equivalent terms as FULL matches. Do NOT penalize for linguistic form:
   - Noun/adjective/verb forms of the same concept are EQUAL:
     "analiza produktow" = "analiza produktowa" = "product analysis" = "analizowanie produktow"
     "zarzadzanie projektem" = "project management" = "zarzadzanie projektami" = "PM"
     "testowanie oprogramowania" = "software testing" = "testy oprogramowania"
     "obsluga klienta" = "customer service" = "customer support" = "wsparcie klienta"
   - Polish <-> English equivalents are FULL matches:
     "programowanie" = "programming", "sprzedaz" = "sales", "rekrutacja" = "recruitment"
     "kierownik" = "manager", "analityk" = "analyst", "deweloper" = "developer"
     "ksiegowosc" = "accounting", "marketing" = "marketing", "logistyka" = "logistics"
   - Abbreviations = full name (FULL match):
     "ML" = "Machine Learning", "AI" = "Artificial Intelligence"
     "PM" = "Project Manager", "UX" = "User Experience", "QA" = "Quality Assurance"
     "BA" = "Business Analyst", "HR" = "Human Resources", "IT" = "Information Technology"
   - Industry synonyms are FULL matches:
     "Excel" = "Microsoft Excel" = "arkusze kalkulacyjne" = "spreadsheets"
     "SQL" = "bazy danych SQL" = "zapytania SQL" = "database querying"
     "Python" = "programowanie w Python" = "skrypty Python"
2. Partial semantic match -> proportional score (NOT zero):
   - Related domain (e.g. "analiza danych" for "analiza rynku") -> 40-60%
   - Transferable skill (e.g. "sprzedaz B2C" for "sprzedaz B2B") -> 50-70%
3. Do NOT deduct for formatting, typos, or case differences.

"""

# ---------------------------------------------------------------------------
# Prompt 1: Minimalna ekstrakcja (name, skills, experience, education)
# ---------------------------------------------------------------------------
EXTRACTION_PROMPT = """Extract structured data from this CV.

INSTRUCTIONS:
- Extract ALL skill variants mentioned (Polish and English names, abbreviations, full names).
- If a skill appears in multiple forms (e.g. "Python" and "programowanie w Pythonie"), list all variants in skills[].
- Treat Polish and English equivalents as the same skill — list both forms.
- sections_detected: list all section headings found (e.g. "experience", "education", "skills").

CV TEXT:
{cv_text}

Return JSON:
{{
    "extracted": {{
        "name": "",
        "skills": [],
        "experience_years": null,
        "education": "",
        "sections_detected": [],
        "has_contact_info": false,
        "has_summary": false
    }},
    "problems": [
        {{
            "category": "generic_description|missing_specifics|missing_keywords|structural|formatting|grammar|length|other",
            "severity": "critical|warning|info",
            "title": "",
            "description": "",
            "section": "",
            "affected_text": ""
        }}
    ]
}}"""

# ---------------------------------------------------------------------------
# Prompt 2: Qualitative section-by-section analysis (NO numerical scores)
# ---------------------------------------------------------------------------
SECTION_ANALYSIS_PROMPT = """Analyze this CV qualitatively. Do NOT assign numerical scores.
For each detected section, provide textual analysis: strengths, gaps, and specific improvement suggestions.
For important sections that are MISSING from the CV, note what should be added and why.

LANGUAGE NOTE: Polish and English skill names are equivalent — do NOT flag "Python" vs "programowanie w Pythonie"
as a gap. Treat abbreviations (ML, AI, PM, QA) as equivalent to their full names.

EXTRACTED CV DATA:
{extracted_json}

DETECTED SECTIONS: {sections_list}

PROBLEMS FOUND: {problems_summary}

SECTION CONTENTS:
{sections_content}

Return JSON:
{{
    "summary": "2-4 sentence qualitative summary of the CV - strengths, weaknesses, overall impression. No numbers or scores.",
    "section_analyses": [
        {{
            "section": "section name (e.g. experience, education, skills, summary, projects, certificates, languages, interests)",
            "status": "present|missing|weak",
            "analysis": "2-4 sentences: what is good, what is lacking, what could be improved",
            "suggestions": ["specific actionable suggestion 1", "suggestion 2"]
        }}
    ],
    "recommendations": [
        {{
            "type": "add|remove|rewrite|skill|structure|career",
            "priority": "high|medium|low",
            "title": "",
            "description": "",
            "section": "",
            "suggested_text": ""
        }}
    ],
    "skill_gaps": [
        {{
            "skill_name": "",
            "current_level": "",
            "recommended_level": "",
            "importance": "high|medium|low",
            "learning_resources": ""
        }}
    ]
}}"""

# Legacy prompts for rewriting and job matching (unchanged)
REWRITE_PROMPT = """Rewrite the following CV section to be more professional and ATS-friendly.

SECTION TYPE: {section_type}

ORIGINAL TEXT:
{original_text}

CONTEXT: {problems_context}

Return JSON:
{{
    "rewritten_text": "",
    "improvement_notes": ""
}}"""

JOB_MATCH_PROMPT = (
    "Compare CV against job posting.\n\n"
    + _SEMANTIC_RULES
    + "SCORING INSTRUCTIONS:\n"
    "- Apply semantic matching rules above to ALL comparisons.\n"
    "- match_percentage: 0-100% weighted (skills 40%, experience 30%, education 15%, keywords 15%)\n"
    "- matching_skills: skills candidate HAS that match the job (use job terminology).\n"
    "- missing_skills: list ONLY skills with NO semantic equivalent in the CV.\n"
    "- Do NOT list a skill as missing if a synonym or PL/EN equivalent is present in the CV.\n\n"
    "CV TEXT:\n{cv_text}\n\n"
    "JOB POSTING:\n{job_text}\n\n"
    "Return JSON:\n"
    "{{\n"
    "    \"match_percentage\": 0,\n"
    "    \"matching_skills\": [],\n"
    "    \"missing_skills\": [],\n"
    "    \"keyword_matches\": [],\n"
    "    \"missing_keywords\": [],\n"
    "    \"strengths\": [],\n"
    "    \"weaknesses\": [],\n"
    "    \"recommendations\": [],\n"
    "    \"summary\": \"\"\n"
    "}}"
)
