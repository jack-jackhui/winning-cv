"""
Job Analyzer Service - AI-powered job analysis and matching.
Uses Azure OpenAI for deep analysis of job fit.
"""
import json
import re
import logging
from typing import Dict, List, Optional, Any, Tuple

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import Config
from api.schemas.job_tools import (
    JobItem,
    JobMatchResult,
    MatchRecommendation,
    StrengthDetail,
    GapDetail,
    CoverLetterAngle,
    InterviewPrep,
    AnalysisRecommendation,
)

logger = logging.getLogger(__name__)


class JobAnalyzerService:
    """Service for AI-powered job analysis and matching."""

    def __init__(self):
        self.client = self._init_client()

    def _init_client(self) -> ChatCompletionsClient:
        """Initialize Azure OpenAI client."""
        return ChatCompletionsClient(
            endpoint=Config.AZURE_AI_ENDPOINT,
            credential=AzureKeyCredential(Config.AZURE_AI_API_KEY),
        )

    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """Parse JSON from LLM response, handling markdown code blocks."""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try extracting from code blocks
            patterns = [
                r'```json\s*({.*?})\s*```',
                r'```\s*({.*?})\s*```',
                r'\{.*\}'
            ]
            for pattern in patterns:
                match = re.search(pattern, response_text, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(1) if '```' in pattern else match.group())
                    except json.JSONDecodeError:
                        continue
            logger.error(f"Failed to parse JSON from response: {response_text[:500]}")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _call_llm(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Make LLM API call with retry logic."""
        try:
            response = self.client.complete(
                messages=[
                    SystemMessage(content=system_prompt),
                    UserMessage(content=user_prompt)
                ],
                model=Config.AZURE_DEPLOYMENT,
                model_extras={"max_completion_tokens": 4000}
            )
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content
            return None
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def match_job(self, job: JobItem, cv_text: str) -> JobMatchResult:
        """
        Score a single job against a CV.

        Args:
            job: Job item to match
            cv_text: User's CV text

        Returns:
            JobMatchResult with score, strengths, gaps, and recommendation
        """
        system_prompt = """You are an expert recruiter analyzing job-CV matches.
Analyze the match between the CV and job description. Return a JSON response with:
- score: number 0-10 (decimal allowed)
- strengths: list of 2-5 key matching factors
- gaps: list of 0-3 areas where CV doesn't match well
- recommendation: one of "STRONG_MATCH" (8-10), "GOOD_MATCH" (6-7.9), "WEAK_MATCH" (4-5.9), "NO_MATCH" (0-3.9)

Your response MUST be valid JSON only, no other text.
Example:
{
  "score": 7.5,
  "strengths": ["Relevant AI experience", "Leadership background"],
  "gaps": ["Missing specific industry experience"],
  "recommendation": "GOOD_MATCH"
}"""

        job_desc = job.description or f"Title: {job.title}\nCompany: {job.company}\nLocation: {job.location or 'Not specified'}"

        user_prompt = f"""Job Details:
Title: {job.title}
Company: {job.company}
Location: {job.location or 'Not specified'}
Description:
{job_desc}

CV:
{cv_text[:8000]}

Provide your match analysis as JSON:"""

        try:
            response = self._call_llm(system_prompt, user_prompt)
            if not response:
                return self._default_match_result(job)

            parsed = self._parse_json_response(response)
            if not parsed:
                return self._default_match_result(job)

            score = min(max(float(parsed.get('score', 0)), 0), 10)
            recommendation = self._score_to_recommendation(score)

            return JobMatchResult(
                job=job,
                score=score,
                strengths=parsed.get('strengths', []),
                gaps=parsed.get('gaps', []),
                recommendation=recommendation
            )
        except Exception as e:
            logger.error(f"Job matching failed for {job.title}: {e}")
            return self._default_match_result(job)

    def _score_to_recommendation(self, score: float) -> MatchRecommendation:
        """Convert numeric score to recommendation enum."""
        if score >= 8:
            return MatchRecommendation.STRONG_MATCH
        elif score >= 6:
            return MatchRecommendation.GOOD_MATCH
        elif score >= 4:
            return MatchRecommendation.WEAK_MATCH
        else:
            return MatchRecommendation.NO_MATCH

    def _default_match_result(self, job: JobItem) -> JobMatchResult:
        """Return default match result on error."""
        return JobMatchResult(
            job=job,
            score=0,
            strengths=[],
            gaps=["Unable to analyze - please try again"],
            recommendation=MatchRecommendation.NO_MATCH
        )

    def analyze_job(
        self,
        job_description: str,
        cv_text: str,
        job_title: Optional[str] = None,
        company: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deep analysis of a single job posting against user's CV.

        Args:
            job_description: Full job description text
            cv_text: User's CV text
            job_title: Optional job title for context
            company: Optional company name for context

        Returns:
            Dictionary with detailed analysis results
        """
        system_prompt = """You are an expert career advisor providing deep job fit analysis.
Analyze how well the candidate's CV matches this job and provide comprehensive insights.

Return a JSON response with this exact structure:
{
  "score": 7.5,
  "recommendation": "APPLY",
  "fit_assessment": "Brief 2-3 sentence summary of overall fit",
  "strengths": [
    {"area": "Area name", "evidence": "Specific evidence from CV", "relevance": "high"}
  ],
  "gaps": [
    {"area": "Gap area", "severity": "moderate", "mitigation": "How to address this gap"}
  ],
  "red_flags": ["Any concerning mismatches or issues"],
  "cover_letter_angles": [
    {"angle": "Positioning angle", "key_points": ["Point 1", "Point 2"]}
  ],
  "interview_prep": {
    "likely_questions": ["Question 1", "Question 2"],
    "talking_points": ["Point 1", "Point 2"]
  }
}

Rules:
- score: 0-10 decimal
- recommendation: "APPLY" (score 7+), "CONSIDER" (score 5-6.9), "SKIP" (score <5)
- strengths: 2-5 items, relevance must be "high", "medium", or "low"
- gaps: 0-3 items, severity must be "critical", "moderate", or "minor"
- red_flags: 0-3 items, empty list if none
- cover_letter_angles: 1-3 angles
- interview_prep: 3-5 questions and 3-5 talking points

Your response MUST be valid JSON only."""

        context = ""
        if job_title:
            context += f"Job Title: {job_title}\n"
        if company:
            context += f"Company: {company}\n"

        user_prompt = f"""{context}Job Description:
{job_description[:10000]}

Candidate's CV:
{cv_text[:8000]}

Provide your detailed analysis as JSON:"""

        try:
            response = self._call_llm(system_prompt, user_prompt)
            if not response:
                return self._default_analysis()

            parsed = self._parse_json_response(response)
            if not parsed:
                return self._default_analysis()

            # Validate and transform response
            score = min(max(float(parsed.get('score', 0)), 0), 10)

            # Determine recommendation from score if not provided
            rec_str = parsed.get('recommendation', 'CONSIDER')
            if rec_str not in ['APPLY', 'CONSIDER', 'SKIP']:
                if score >= 7:
                    rec_str = 'APPLY'
                elif score >= 5:
                    rec_str = 'CONSIDER'
                else:
                    rec_str = 'SKIP'

            # Transform strengths
            strengths = []
            for s in parsed.get('strengths', []):
                if isinstance(s, dict):
                    relevance = s.get('relevance', 'medium')
                    if relevance not in ['high', 'medium', 'low']:
                        relevance = 'medium'
                    strengths.append(StrengthDetail(
                        area=s.get('area', 'Unknown'),
                        evidence=s.get('evidence', ''),
                        relevance=relevance
                    ))

            # Transform gaps
            gaps = []
            for g in parsed.get('gaps', []):
                if isinstance(g, dict):
                    severity = g.get('severity', 'moderate')
                    if severity not in ['critical', 'moderate', 'minor']:
                        severity = 'moderate'
                    gaps.append(GapDetail(
                        area=g.get('area', 'Unknown'),
                        severity=severity,
                        mitigation=g.get('mitigation', '')
                    ))

            # Transform cover letter angles
            cover_letters = []
            for c in parsed.get('cover_letter_angles', []):
                if isinstance(c, dict):
                    cover_letters.append(CoverLetterAngle(
                        angle=c.get('angle', ''),
                        key_points=c.get('key_points', [])
                    ))

            # Transform interview prep
            interview_data = parsed.get('interview_prep', {})
            interview_prep = InterviewPrep(
                likely_questions=interview_data.get('likely_questions', []),
                talking_points=interview_data.get('talking_points', [])
            )

            return {
                'score': score,
                'recommendation': AnalysisRecommendation(rec_str),
                'fit_assessment': parsed.get('fit_assessment', 'Analysis completed'),
                'strengths': strengths,
                'gaps': gaps,
                'red_flags': parsed.get('red_flags', []),
                'cover_letter_angles': cover_letters,
                'interview_prep': interview_prep
            }

        except Exception as e:
            logger.error(f"Job analysis failed: {e}")
            return self._default_analysis()

    def _default_analysis(self) -> Dict[str, Any]:
        """Return default analysis result on error."""
        return {
            'score': 0,
            'recommendation': AnalysisRecommendation.SKIP,
            'fit_assessment': 'Unable to complete analysis. Please try again.',
            'strengths': [],
            'gaps': [],
            'red_flags': ['Analysis could not be completed'],
            'cover_letter_angles': [],
            'interview_prep': InterviewPrep(
                likely_questions=[],
                talking_points=[]
            )
        }

    def batch_match_jobs(
        self,
        jobs: List[JobItem],
        cv_text: str
    ) -> List[JobMatchResult]:
        """
        Match multiple jobs against a CV.

        Args:
            jobs: List of jobs to match
            cv_text: User's CV text

        Returns:
            List of JobMatchResult sorted by score descending
        """
        results = []
        for job in jobs:
            result = self.match_job(job, cv_text)
            results.append(result)

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        return results
