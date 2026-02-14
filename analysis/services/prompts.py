"""analysis/services/prompts.py - Prompty dla OpenAI GPT.

Pipeline:
1. EXTRACTION_PROMPT - ekstrakcja danych + wykrywanie problemow → JSON
2. SECTION_ANALYSIS_PROMPT - jakosciowa analiza sekcji CV → JSON (bez ocen numerycznych)
"""

SYSTEM_PROMPT = "You are a CV analyst. Respond only in valid JSON."

# ---------------------------------------------------------------------------
# Prompt 1: Minimalna ekstrakcja (name, skills, experience, education)
# ---------------------------------------------------------------------------
EXTRACTION_PROMPT = """Extract from CV:

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

JOB_MATCH_PROMPT = """Compare CV against job posting.

CV TEXT:
{cv_text}

JOB POSTING:
{job_text}

Return JSON:
{{
    "match_percentage": 0,
    "matching_skills": [],
    "missing_skills": [],
    "keyword_matches": [],
    "missing_keywords": [],
    "strengths": [],
    "weaknesses": [],
    "recommendations": [],
    "summary": ""
}}"""
