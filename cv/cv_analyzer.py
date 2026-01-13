# cv/cv_analyzer.py
"""
CV-JD Fit Analysis Engine

Analyzes a generated CV against a job description to provide:
- Overall match score
- Keyword match analysis
- Skills coverage assessment
- Experience relevance evaluation
- ATS optimization score
- Gap analysis
- Interview talking points
"""

import os
import json
import logging
import re
from typing import Optional
from dataclasses import dataclass, asdict
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

logger = logging.getLogger(__name__)


@dataclass
class KeywordMatch:
    score: int  # 0-100
    matched: list[str]
    missing: list[str]
    density_assessment: str


@dataclass
class TechnicalSkills:
    matched: list[str]
    partial: list[str]
    missing: list[str]


@dataclass
class SoftSkills:
    matched: list[str]
    demonstrated: list[str]


@dataclass
class SkillsCoverage:
    score: int
    technical_skills: TechnicalSkills
    soft_skills: SoftSkills


@dataclass
class ExperienceRelevance:
    score: int
    aligned_roles: list[str]
    relevant_achievements: list[str]
    years_alignment: str


@dataclass
class ATSOptimization:
    score: int
    format_check: bool
    keyword_density: str
    section_structure: str
    recommendations: list[str]


@dataclass
class GapAnalysis:
    critical_gaps: list[str]
    minor_gaps: list[str]
    mitigation_suggestions: list[str]


@dataclass
class TalkingPoints:
    strengths_to_highlight: list[str]
    questions_to_prepare: list[str]
    stories_to_ready: list[str]


@dataclass
class CVAnalysis:
    overall_score: int
    summary: str
    keyword_match: KeywordMatch
    skills_coverage: SkillsCoverage
    experience_relevance: ExperienceRelevance
    ats_optimization: ATSOptimization
    gap_analysis: GapAnalysis
    talking_points: TalkingPoints

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


# Analysis system prompt
CV_ANALYSIS_SYSTEM_PROMPT = """
## Role
You are an expert CV/Resume Analyst and Career Coach specializing in job application optimization.

## Task
Analyze the provided CV against the job description to produce a comprehensive fit analysis.
Your analysis must be honest, actionable, and based solely on the content provided.

## Output Format
You MUST respond with ONLY a valid JSON object matching this exact structure:

{
  "overall_score": <integer 0-100>,
  "summary": "<2-3 sentence executive summary of the fit>",
  "keyword_match": {
    "score": <integer 0-100>,
    "matched": ["<keyword1>", "<keyword2>", ...],
    "missing": ["<important keyword not in CV>", ...],
    "density_assessment": "<Good|Adequate|Needs Improvement>"
  },
  "skills_coverage": {
    "score": <integer 0-100>,
    "technical_skills": {
      "matched": ["<skill1>", "<skill2>", ...],
      "partial": ["<related but not exact skill>", ...],
      "missing": ["<required skill not in CV>", ...]
    },
    "soft_skills": {
      "matched": ["<soft skill explicitly mentioned>", ...],
      "demonstrated": ["<soft skill implied through achievements>", ...]
    }
  },
  "experience_relevance": {
    "score": <integer 0-100>,
    "aligned_roles": ["<role that matches JD requirements>", ...],
    "relevant_achievements": ["<achievement supporting fit>", ...],
    "years_alignment": "<assessment of experience level match>"
  },
  "ats_optimization": {
    "score": <integer 0-100>,
    "format_check": <true if clean formatting>,
    "keyword_density": "<Good|Adequate|Low>",
    "section_structure": "<Clear|Acceptable|Needs Work>",
    "recommendations": ["<specific ATS improvement>", ...]
  },
  "gap_analysis": {
    "critical_gaps": ["<must-have requirement not met>", ...],
    "minor_gaps": ["<nice-to-have not present>", ...],
    "mitigation_suggestions": ["<how to address gap in interview>", ...]
  },
  "talking_points": {
    "strengths_to_highlight": ["<key strength to emphasize in interview>", ...],
    "questions_to_prepare": ["<likely interview question based on JD>", ...],
    "stories_to_ready": ["<STAR story suggestion based on CV content>", ...]
  }
}

## Scoring Guidelines
- 90-100: Exceptional fit - CV strongly matches all key requirements
- 75-89: Strong fit - CV matches most requirements with minor gaps
- 60-74: Moderate fit - CV matches core requirements but has notable gaps
- 40-59: Weak fit - Significant gaps in key areas
- 0-39: Poor fit - Major misalignment with job requirements

## Analysis Guidelines
1. Be specific - use actual keywords and skills from the documents
2. Be honest - don't inflate scores or ignore gaps
3. Be actionable - provide concrete interview preparation advice
4. Be concise - limit lists to 5-8 most important items each
5. Focus on what matters most to hiring managers

## CRITICAL
- Output ONLY the JSON object, no markdown code blocks, no explanations
- Ensure all JSON is properly formatted and valid
- All scores must be integers between 0 and 100
"""


def _clean_json_response(text: str) -> str:
    """Clean LLM response to extract valid JSON."""
    # Remove markdown code blocks if present
    text = re.sub(r'^```(?:json)?\s*\n?', '', text.strip())
    text = re.sub(r'\n?```\s*$', '', text.strip())

    # Remove any <think> blocks
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

    return text


def _parse_analysis_response(response_text: str) -> CVAnalysis:
    """Parse LLM response into CVAnalysis dataclass."""
    cleaned = _clean_json_response(response_text)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse analysis JSON: {e}")
        logger.error(f"Response text: {cleaned[:500]}...")
        raise ValueError(f"Invalid JSON in analysis response: {e}")

    # Build nested dataclasses
    keyword_match = KeywordMatch(
        score=data["keyword_match"]["score"],
        matched=data["keyword_match"]["matched"],
        missing=data["keyword_match"]["missing"],
        density_assessment=data["keyword_match"]["density_assessment"]
    )

    skills_coverage = SkillsCoverage(
        score=data["skills_coverage"]["score"],
        technical_skills=TechnicalSkills(
            matched=data["skills_coverage"]["technical_skills"]["matched"],
            partial=data["skills_coverage"]["technical_skills"]["partial"],
            missing=data["skills_coverage"]["technical_skills"]["missing"]
        ),
        soft_skills=SoftSkills(
            matched=data["skills_coverage"]["soft_skills"]["matched"],
            demonstrated=data["skills_coverage"]["soft_skills"]["demonstrated"]
        )
    )

    experience_relevance = ExperienceRelevance(
        score=data["experience_relevance"]["score"],
        aligned_roles=data["experience_relevance"]["aligned_roles"],
        relevant_achievements=data["experience_relevance"]["relevant_achievements"],
        years_alignment=data["experience_relevance"]["years_alignment"]
    )

    ats_optimization = ATSOptimization(
        score=data["ats_optimization"]["score"],
        format_check=data["ats_optimization"]["format_check"],
        keyword_density=data["ats_optimization"]["keyword_density"],
        section_structure=data["ats_optimization"]["section_structure"],
        recommendations=data["ats_optimization"]["recommendations"]
    )

    gap_analysis = GapAnalysis(
        critical_gaps=data["gap_analysis"]["critical_gaps"],
        minor_gaps=data["gap_analysis"]["minor_gaps"],
        mitigation_suggestions=data["gap_analysis"]["mitigation_suggestions"]
    )

    talking_points = TalkingPoints(
        strengths_to_highlight=data["talking_points"]["strengths_to_highlight"],
        questions_to_prepare=data["talking_points"]["questions_to_prepare"],
        stories_to_ready=data["talking_points"]["stories_to_ready"]
    )

    return CVAnalysis(
        overall_score=data["overall_score"],
        summary=data["summary"],
        keyword_match=keyword_match,
        skills_coverage=skills_coverage,
        experience_relevance=experience_relevance,
        ats_optimization=ats_optimization,
        gap_analysis=gap_analysis,
        talking_points=talking_points
    )


class CVAnalyzer:
    """Analyzes CV-JD fit using Azure OpenAI."""

    def __init__(self):
        self.endpoint = os.getenv("AZURE_AI_ENDPOINT")
        self.key = os.getenv("AZURE_AI_API_KEY")
        self.model_name = os.getenv("AZURE_DEPLOYMENT")

    def _get_client(self) -> ChatCompletionsClient:
        return ChatCompletionsClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(self.key)
        )

    def analyze(self, cv_markdown: str, job_description: str) -> CVAnalysis:
        """
        Analyze a CV against a job description.

        Args:
            cv_markdown: The generated CV content in markdown format
            job_description: The job description used for tailoring

        Returns:
            CVAnalysis object with comprehensive fit analysis

        Raises:
            ValueError: If inputs are empty or analysis fails to parse
            Exception: If LLM call fails
        """
        if not cv_markdown.strip():
            raise ValueError("Empty CV content")
        if not job_description.strip():
            raise ValueError("Empty job description")

        try:
            client = self._get_client()

            user_message = f"""Analyze the following CV against the job description and provide a comprehensive fit analysis.

## Job Description
{job_description}

## Generated CV
{cv_markdown}

---

Provide your analysis as a JSON object following the exact structure specified in the system prompt.
"""

            response = client.complete(
                messages=[
                    SystemMessage(content=CV_ANALYSIS_SYSTEM_PROMPT),
                    UserMessage(content=user_message)
                ],
                model=self.model_name,
                model_extras={"max_completion_tokens": 8192}
            )

            response_text = response.choices[0].message.content
            logger.debug(f"Analysis response: {response_text[:500]}...")

            analysis = _parse_analysis_response(response_text)
            logger.info(f"CV analysis complete - overall score: {analysis.overall_score}")

            return analysis

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"CV analysis failed: {e}")
            raise Exception(f"CV analysis failed: {str(e)}")


def analyze_cv_fit(cv_markdown: str, job_description: str) -> dict:
    """
    Convenience function to analyze CV-JD fit.

    Args:
        cv_markdown: The generated CV content
        job_description: The job description

    Returns:
        Dictionary containing the analysis results
    """
    analyzer = CVAnalyzer()
    analysis = analyzer.analyze(cv_markdown, job_description)
    return analysis.to_dict()
