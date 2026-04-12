"""recruitment/services/prompts.py - Prompty AI dla modulu rekrutacji.

Wszystkie prompty dopasowania zawieraja reguly semantyczne:
synonimy, formy gramatyczne i odpowiedniki PL/EN traktowane jako pelne dopasowanie.
"""

SYSTEM_PROMPT = "You are an HR recruitment analyst. Respond only in valid JSON."

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
# Prompt 1: PROFILE EXTRACTION — CV -> structured profile + red flags + tags
# ---------------------------------------------------------------------------
PROFILE_EXTRACTION_PROMPT = """Extract structured candidate profile from CV.

CV TEXT:
{cv_text}

INSTRUCTIONS:
- Extract ALL skill variants mentioned (Polish and English names, abbreviations, full names).
- If a skill appears in multiple forms, list all variants in skills[].
- For skill_levels: use exact skill names as they appear in the CV.
- red_flags: flag only genuine concerns (gaps >6 months, >3 short stints <12mo, clear inconsistencies).
- hr_summary: factual 1-2 paragraphs useful for a recruiter making a hiring decision.

Return JSON:
{{
    "profile": {{
        "name": "",
        "email": "",
        "phone": "",
        "location": "",
        "current_role": "",
        "years_of_experience": null,
        "seniority_level": "intern|junior|mid|senior|lead|principal",
        "skills": [],
        "skill_levels": {{"Python": "Advanced", "SQL": "Intermediate"}},
        "education": [{{"degree": "", "institution": "", "year": null}}],
        "companies": [{{"company": "", "role": "", "duration_months": null, "start_year": null, "end_year": null}}],
        "languages": [],
        "certifications": []
    }},
    "hr_summary": "1-2 paragraph summary of candidate for recruiter.",
    "red_flags": [
        {{"type": "job_hopping|employment_gap|overqualified|inconsistency|no_progression",
          "severity": "critical|warning|info",
          "description": ""}}
    ],
    "tags": ["senior", "backend", "remote-ready"]
}}"""

# ---------------------------------------------------------------------------
# Prompt 2: BATCH POSITION MATCHING — 1 candidate vs ALL positions in 1 call
# ---------------------------------------------------------------------------
BATCH_MATCH_PROMPT = (
    "Match candidate against ALL job positions. Return scores for each.\n\n"
    + _SEMANTIC_RULES
    + "CANDIDATE:\n{profile_json}\n\n"
    + "JOB POSITIONS:\n{positions_json}\n\n"
    + """SCORING INSTRUCTIONS:
- Apply semantic matching rules above to ALL comparisons.
- overall_match = weighted average: skills 40% + experience 30% + seniority 20% + education 10%
- matching_skills: list skills candidate HAS that match position requirements (use position terminology).
- missing_skills: list ONLY skills with NO semantic equivalent in candidate profile.
- fit_recommendation: strong_fit >=85%, good_fit >=70%, moderate_fit >=55%, weak_fit >=35%, not_recommended <35%

Return JSON with match for EACH position by its id:
{{
    "matches": [
        {{
            "position_id": "<id>",
            "scores": {{
                "overall_match": 0,
                "skill_match": 0,
                "experience_match": 0,
                "seniority_match": 0,
                "education_match": 0
            }},
            "matching_skills": [],
            "missing_skills": [],
            "fit_recommendation": "strong_fit|good_fit|moderate_fit|weak_fit|not_recommended"
        }}
    ]
}}"""
)

# ---------------------------------------------------------------------------
# Prompt 3 (fallback): SINGLE POSITION MATCHING — 1 candidate vs 1 position
# ---------------------------------------------------------------------------
POSITION_MATCH_PROMPT = (
    "Match candidate against job position.\n\n"
    + _SEMANTIC_RULES
    + "CANDIDATE:\n{profile_json}\n\n"
    + "POSITION:\n{position_json}\n\n"
    + """SCORING INSTRUCTIONS:
- Apply semantic matching rules above to ALL comparisons.
- overall_match = weighted average: skills 40% + experience 30% + seniority 20% + education 10%
- matching_skills: list skills candidate HAS that match position (use position terminology).
- missing_skills: list ONLY skills with NO semantic equivalent in candidate profile.
- fit_recommendation: strong_fit >=85%, good_fit >=70%, moderate_fit >=55%, weak_fit >=35%, not_recommended <35%

Return JSON:
{{
    "scores": {{
        "overall_match": 0,
        "skill_match": 0,
        "experience_match": 0,
        "seniority_match": 0,
        "education_match": 0
    }},
    "matching_skills": [],
    "missing_skills": [],
    "fit_recommendation": "strong_fit|good_fit|moderate_fit|weak_fit|not_recommended"
}}"""
)

# ---------------------------------------------------------------------------
# Prompt 4: INTERVIEW QUESTIONS — based on profile + position
# ---------------------------------------------------------------------------
INTERVIEW_QUESTIONS_PROMPT = """Generate 5-8 interview questions for this candidate and position.

CANDIDATE: {candidate_name}
PROFILE: {profile_summary}
POSITION: {position_title}
MISSING SKILLS: {missing_skills}

INSTRUCTIONS:
- Make questions specific to this candidate's actual background, not generic.
- For missing skills: ask questions that reveal transferable competencies.
- Mix categories: technical, behavioral, situational, cultural.
- why_ask should explain what gap or strength this question probes.

Return JSON:
{{
    "questions": [
        {{
            "category": "technical|behavioral|situational|cultural",
            "question": "",
            "focus_area": "",
            "why_ask": ""
        }}
    ]
}}"""

# ---------------------------------------------------------------------------
# Prompt 5: REQUIREMENT-BY-REQUIREMENT MATCHING
# ---------------------------------------------------------------------------
REQUIREMENT_MATCH_PROMPT = (
    "You are an HR matching engine.\n"
    "For each requirement below, evaluate how well the CV matches it (0-100%).\n"
    "Provide a short explanation for each. Return structured JSON only.\n\n"
    + _SEMANTIC_RULES
    + """SCORING EDGE CASES:
- CV has no info about the requirement -> 0%
- Requirement not measurable -> max 50%
- CV exceeds the requirement -> 100%
- Semantically equivalent skill/experience -> same score as exact match

Requirements:
{requirements_json}

CV:
{cv_text}

Return JSON:
{{
    "requirements": [
        {{
            "requirement": "exact text of the requirement",
            "match_percentage": 0,
            "explanation": "short explanation; note if synonym or equivalent was used"
        }}
    ]
}}"""
)

# ---------------------------------------------------------------------------
# Prompt 7: CANDIDATE INTELLIGENCE LAYER — Premium/Enterprise
# ---------------------------------------------------------------------------
CANDIDATE_INTELLIGENCE_PROMPT = """Analyse this candidate profile and produce a structured intelligence report.

CANDIDATE PROFILE:
{profile_json}

INSTRUCTIONS:
- skill_fit.score: 0-100, how strong is the candidate's overall skill set.
- skill_fit.strong_skills: list of 2-5 skills they excel at.
- skill_fit.weak_skills: list of 0-3 clear gaps or underdeveloped areas.
- skill_fit.summary: 1 sentence.
- learnability.score: 0-100, estimated learning potential based on career progression speed, diversity of technologies, number of roles.
- learnability.signals: list of 2-4 short evidence strings (e.g. "Switched from Java to Python within 1 year").
- career_trajectory.type: "ascending" | "lateral" | "stagnant" | "early" (ascending=clear progression, lateral=same level moves, stagnant=no growth, early=<3 yrs total).
- career_trajectory.summary: 1 short sentence.
- behavioral_signals: 2-5 items, each {{signal: "...", type: "positive"|"negative"|"neutral"}}.
- risk_flags: 0-3 items ONLY for genuine concerns: {{flag: "...", severity: "high"|"medium"|"low"}}. Omit if none.
- confidence: "high" if CV is complete and detailed, "medium" if partially filled, "low" if sparse.
- recommendation: "invite" if strong overall fit, "consider" if mixed, "reject" if major red flags or severe skill gaps.
- recommendation_reason: 1-2 sentences explaining the recommendation.

Return JSON only:
{{
    "skill_fit": {{
        "score": 0,
        "strong_skills": [],
        "weak_skills": [],
        "summary": ""
    }},
    "learnability": {{
        "score": 0,
        "signals": []
    }},
    "career_trajectory": {{
        "type": "ascending",
        "summary": ""
    }},
    "behavioral_signals": [
        {{"signal": "", "type": "positive"}}
    ],
    "risk_flags": [],
    "confidence": "medium",
    "recommendation": "consider",
    "recommendation_reason": ""
}}"""

# ---------------------------------------------------------------------------
# Prompt 6: SECTION SCORING — per-section CV evaluation against position
# ---------------------------------------------------------------------------
SECTION_SCORE_PROMPT = (
    "You are an HR evaluation engine.\n"
    "Evaluate how well this CV section matches the job position.\n"
    "Return match percentage (0-100) and short analysis (2-4 sentences).\n\n"
    + _SEMANTIC_RULES
    + """SCORING EDGE CASES:
- Section empty or irrelevant -> 0%
- Section partially matches -> proportional score
- Section exceeds requirements -> 100%
- Semantically equivalent content -> same score as exact match

JOB REQUIREMENTS:
{position_requirements}

CV SECTION NAME:
{section_name}

CV SECTION CONTENT:
{section_text}

Return JSON:
{{
    "score": 0,
    "analysis": "..."
}}"""
)
