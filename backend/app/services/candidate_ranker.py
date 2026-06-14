"""
Candidate Ranker Service
Uses Google Gemini to rank a candidate against a Job Description.
"""
import json
import logging
import re
from typing import Any, Dict

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_client() -> genai.Client:
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _clean_json_response(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


async def rank_candidate(
    jd_data: Dict[str, Any],
    candidate_parsed_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Rank a candidate against a job description using Gemini.

    Args:
        jd_data: Job description dict with title, department, responsibilities,
                 required_skills, preferred_skills, experience_requirements, seniority_level
        candidate_parsed_data: Parsed CV data from cv_parser

    Returns:
        Dict with scoring results:
            skills_match, experience_match, education_match,
            domain_knowledge, communication_indicators,
            overall_score, recommendation_level, summary
    """
    client = _get_client()

    jd_text = f"""
Job Title: {jd_data.get('title', 'N/A')}
Department: {jd_data.get('department', 'N/A')}
Seniority Level: {jd_data.get('seniority_level', 'N/A')}
Experience Requirements: {jd_data.get('experience_requirements', 'N/A')}
Responsibilities: {jd_data.get('responsibilities', 'N/A')}
Required Skills: {', '.join(jd_data.get('required_skills', []))}
Preferred Skills: {', '.join(jd_data.get('preferred_skills', []) or [])}
"""

    cv_text = f"""
Candidate Name: {candidate_parsed_data.get('name', 'N/A')}
Skills: {', '.join(candidate_parsed_data.get('skills', []))}
Education: {json.dumps(candidate_parsed_data.get('education', []), ensure_ascii=False)}
Work Experience: {json.dumps(candidate_parsed_data.get('work_experience', []), ensure_ascii=False)}
Certifications: {', '.join(candidate_parsed_data.get('certifications', []))}
Summary: {candidate_parsed_data.get('summary', '')}
"""

    prompt = f"""
You are an expert HR talent acquisition specialist. Evaluate this candidate against the job description and provide detailed scoring.

JOB DESCRIPTION:
{jd_text}

CANDIDATE PROFILE:
{cv_text}

Analyze and score the candidate on these dimensions (0-100 scale):

1. **Skills Match**: How well do the candidate's skills match the required and preferred skills?
2. **Experience Match**: Does the candidate's experience level and years match the requirements?
3. **Education Match**: Does the candidate's educational background fit the role?
4. **Domain Knowledge**: Does the candidate have relevant domain/industry knowledge?
5. **Communication Indicators**: Based on CV quality, structure, and articulation of achievements - indicators of communication skills.
6. **Overall Score**: Weighted average (Skills: 30%, Experience: 30%, Domain: 20%, Education: 10%, Communication: 10%)

Return ONLY a valid JSON object with this exact structure:
{{
  "skills_match": <float 0-100>,
  "experience_match": <float 0-100>,
  "education_match": <float 0-100>,
  "domain_knowledge": <float 0-100>,
  "communication_indicators": <float 0-100>,
  "overall_score": <float 0-100>,
  "recommendation_level": "<strong_match|moderate_match|weak_match>",
  "summary": "Detailed explanation of the assessment in 3-5 sentences covering strengths and gaps",
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "gaps": ["gap 1", "gap 2"]
}}

Recommendation level guidelines:
- strong_match: overall_score >= 75
- moderate_match: overall_score >= 50
- weak_match: overall_score < 50

Return ONLY the JSON object, no other text.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=2048,
            ),
        )
        raw_json = _clean_json_response(response.text)
        result = json.loads(raw_json)

        for field in [
            "skills_match",
            "experience_match",
            "education_match",
            "domain_knowledge",
            "communication_indicators",
            "overall_score",
        ]:
            val = result.get(field, 0)
            result[field] = max(0.0, min(100.0, float(val)))

        valid_levels = {"strong_match", "moderate_match", "weak_match"}
        if result.get("recommendation_level") not in valid_levels:
            score = result.get("overall_score", 0)
            if score >= 75:
                result["recommendation_level"] = "strong_match"
            elif score >= 50:
                result["recommendation_level"] = "moderate_match"
            else:
                result["recommendation_level"] = "weak_match"

        result.setdefault("summary", "No summary provided.")
        result.setdefault("strengths", [])
        result.setdefault("gaps", [])

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Gemini returned invalid JSON for ranking: {e}")
        return {
            "skills_match": 50.0,
            "experience_match": 50.0,
            "education_match": 50.0,
            "domain_knowledge": 50.0,
            "communication_indicators": 50.0,
            "overall_score": 50.0,
            "recommendation_level": "moderate_match",
            "summary": "Unable to complete full analysis. Manual review recommended.",
            "strengths": [],
            "gaps": [],
        }
    except Exception as e:
        logger.error(f"Gemini ranking failed: {e}")
        raise RuntimeError(f"Candidate ranking failed: {e}")
