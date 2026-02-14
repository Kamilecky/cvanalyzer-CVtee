"""recruitment/services/prompts.py - Minimalne prompty AI dla modułu rekrutacji."""

SYSTEM_PROMPT = "You are an HR recruitment analyst. Respond only in valid JSON."

# ---------------------------------------------------------------------------
# Prompt 1: PROFILE EXTRACTION — CV → structured profile + red flags + summary + tags + skill levels
# ---------------------------------------------------------------------------
PROFILE_EXTRACTION_PROMPT = """Extract structured candidate profile from CV.

CV TEXT:
{cv_text}

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
BATCH_MATCH_PROMPT = """Match candidate against ALL job positions. Return scores for each.

CANDIDATE:
{profile_json}

JOB POSITIONS:
{positions_json}

Return JSON with match for EACH position by its id:
{{
    "matches": [
        {{
            "position_id": "<id>",
            "scores": {{
                "overall_match": 0-100,
                "skill_match": 0-100,
                "experience_match": 0-100,
                "seniority_match": 0-100,
                "education_match": 0-100
            }},
            "matching_skills": [],
            "missing_skills": [],
            "fit_recommendation": "strong_fit|good_fit|moderate_fit|weak_fit|not_recommended"
        }}
    ]
}}"""

# ---------------------------------------------------------------------------
# Prompt 3 (fallback): SINGLE POSITION MATCHING — 1 candidate vs 1 position
# ---------------------------------------------------------------------------
POSITION_MATCH_PROMPT = """Match candidate against job position.

CANDIDATE:
{profile_json}

POSITION:
{position_json}

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

# ---------------------------------------------------------------------------
# Prompt 5: REQUIREMENT-BY-REQUIREMENT MATCHING — 1 CV vs 1 position, per-requirement scores
# ---------------------------------------------------------------------------
REQUIREMENT_MATCH_PROMPT = """You are an HR matching engine.
For each requirement below, evaluate how well the CV matches it (0-100%).
Provide a short explanation for each.
Return structured JSON only.

Edge cases:
- If CV has no info about the requirement → 0%
- If requirement is not measurable → max 50%
- If CV exceeds the requirement → 100%

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
            "explanation": "short explanation why this score"
        }}
    ]
}}"""

# ---------------------------------------------------------------------------
# Prompt 4: INTERVIEW QUESTIONS — based on profile + position
# ---------------------------------------------------------------------------
INTERVIEW_QUESTIONS_PROMPT = """Generate 5-8 interview questions for this candidate and position.

CANDIDATE: {candidate_name}
PROFILE: {profile_summary}
POSITION: {position_title}
MISSING SKILLS: {missing_skills}

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
# Prompt 6: SECTION SCORING — per-section CV evaluation against position
# ---------------------------------------------------------------------------
SECTION_SCORE_PROMPT = """You are an HR evaluation engine.
Evaluate how well this CV section matches the job position.
Return match percentage (0-100) and short analysis (2-4 sentences).

Edge cases:
- If section is empty or irrelevant → 0%
- If section partially matches → proportional score
- If section exceeds requirements → 100%

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
